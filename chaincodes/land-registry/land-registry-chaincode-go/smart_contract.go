package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/pkg/cid"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

func saveState(ctx contractapi.TransactionContextInterface, key string, obj interface{}) error {
	b, err := json.Marshal(obj)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(key, b)
}

func getInvokerID(ctx contractapi.TransactionContextInterface) (string, error) {
	ci, err := cid.New(ctx.GetStub())
	if err != nil {
		return "", err
	}
	id, found, err := ci.GetAttributeValue("hf.EnrollmentID")
	if err != nil || !found {
		return "", errors.New("unable to resolve invoker id")
	}
	return id, nil
}

func getInvokerName(ctx contractapi.TransactionContextInterface) string {
	transientMap, _ := ctx.GetStub().GetTransient()
	if raw, ok := transientMap["byUserName"]; ok {
		return string(raw)
	}
	return ""
}

func checkOffice(ctx contractapi.TransactionContextInterface, expectedMSP string, expectedOffice string) error {
	ci, err := cid.New(ctx.GetStub())
	if err != nil {
		return err
	}
	msp, _ := ci.GetMSPID()
	if msp != expectedMSP {
		return fmt.Errorf("only %s can perform this action", expectedMSP)
	}
	office, _, _ := ci.GetAttributeValue("kataster.office")
	if office != expectedOffice {
		return fmt.Errorf("invalid office: %s", office)
	}
	return nil
}

func addStatusChange(ctx contractapi.TransactionContextInterface, req *ChangeRequest, newStatus string) {
	invoker, _ := getInvokerID(ctx)
	name := getInvokerName(ctx)
	if name == "" {
		name = invoker
	}

	ts, _ := ctx.GetStub().GetTxTimestamp()
	at := time.Unix(ts.Seconds, 0).UTC().Format(time.RFC3339)

	req.StatusHistory = append(req.StatusHistory, StatusChange{
		FromStatus: req.Status,
		ToStatus:   newStatus,
		ByUserID:   invoker,
		ByUserName: name,
		At:         at,
		TxID:       ctx.GetStub().GetTxID(),
	})
	req.Status = newStatus
}

func (s *SmartContract) CreateParcel(ctx contractapi.TransactionContextInterface, parcelJSON string) (*Parcel, error) {
	var parcel Parcel
	if err := json.Unmarshal([]byte(parcelJSON), &parcel); err != nil {
		return nil, fmt.Errorf("invalid parcel JSON: %v", err)
	}
	parcel.DocType = "parcel"

	if parcel.ID == "" || parcel.ParcelID == "" || len(parcel.Owners) == 0 || len(parcel.Points) < 3 {
		return nil, errors.New("missing required parcel fields")
	}

	existing, _ := ctx.GetStub().GetState(parcel.ID)
	if existing != nil {
		return nil, fmt.Errorf("parcel %s already exists", parcel.ID)
	}

	err := saveState(ctx, parcel.ID, parcel)
	if err != nil {
		return nil, err
	}
	return &parcel, nil
}

func (s *SmartContract) ReadParcel(ctx contractapi.TransactionContextInterface, id string) (*Parcel, error) {
	b, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("parcel %s does not exist", id)
	}
	var parcel Parcel
	json.Unmarshal(b, &parcel)
	parcel.ID = id
	return &parcel, nil
}

func (s *SmartContract) GetAllParcels(ctx contractapi.TransactionContextInterface) ([]*Parcel, error) {
	iter, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer iter.Close()

	var parcels []*Parcel
	for iter.HasNext() {
		kv, err := iter.Next()
		if err != nil {
			return nil, err
		}
		var p Parcel
		if json.Unmarshal(kv.Value, &p) == nil && p.DocType == "parcel" {
			parcels = append(parcels, &p)
		}
	}
	return parcels, nil
}

func (s *SmartContract) ReadChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	b, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, err
	}
	if b == nil {
		return nil, fmt.Errorf("change request %s does not exist", id)
	}
	var req ChangeRequest
	json.Unmarshal(b, &req)
	req.ID = id
	return &req, nil
}

func (s *SmartContract) GetAllChangeRequests(ctx contractapi.TransactionContextInterface) ([]*ChangeRequest, error) {
	iter, err := ctx.GetStub().GetStateByRange("", "")
	if err != nil {
		return nil, err
	}
	defer iter.Close()

	var reqs []*ChangeRequest
	for iter.HasNext() {
		kv, err := iter.Next()
		if err != nil {
			return nil, err
		}
		var r ChangeRequest
		if json.Unmarshal(kv.Value, &r) == nil && r.DocType == "changeRequest" {
			reqs = append(reqs, &r)
		}
	}
	return reqs, nil
}

func (s *SmartContract) CreateChangeRequest(ctx contractapi.TransactionContextInterface, requestJSON string) (*ChangeRequest, error) {
	var req ChangeRequest
	if err := json.Unmarshal([]byte(requestJSON), &req); err != nil {
		return nil, fmt.Errorf("invalid request JSON: %v", err)
	}

	req.DocType = "changeRequest"
	req.ID = ctx.GetStub().GetTxID()

	if req.ParcelID == "" || req.RequesterUserID == "" || req.ChangeJSON == "" {
		return nil, errors.New("parcelId, requesterUserId, and changeJson are required")
	}

	invoker, err := getInvokerID(ctx)
	if err != nil {
		return nil, err
	}
	if invoker != req.RequesterUserID {
		return nil, errors.New("requesterUserId must match invoker")
	}

	parcel, err := s.ReadParcel(ctx, req.ParcelID)
	if err != nil {
		return nil, err
	}

	isOwner := false
	for _, o := range parcel.Owners {
		if o.UserID == invoker {
			isOwner = true
			break
		}
	}
	if !isOwner {
		return nil, errors.New("only parcel owner can create change request")
	}

	// Check if parcel already has an active sale
	locked, err := parcelHasActiveSale(ctx, req.ParcelID, "")
	if err != nil {
		return nil, err
	}
	if locked {
		return nil, errors.New("parcel is locked due to an active sale")
	}

	// If it's a transfer, extract buyer info
	var payload changePayload
	json.Unmarshal([]byte(req.ChangeJSON), &payload)
	if payload.Type == "TRANSFER_SHARE" {
		if payload.ToUserID == "" {
			return nil, errors.New("toUserId is required for TRANSFER_SHARE")
		}
		if payload.ToUserID == req.RequesterUserID {
			return nil, errors.New("buyer and requester must be different")
		}
		req.BuyerUserID = payload.ToUserID
	}

	addStatusChange(ctx, &req, "SUBMITTED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	key, _ := ctx.GetStub().CreateCompositeKey("sale", []string{req.ParcelID, req.ID})
	ctx.GetStub().PutState(key, []byte{0x00})
	return &req, nil
}

func (s *SmartContract) BuyerApproveChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "SUBMITTED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	invoker, err := getInvokerID(ctx)
	if err != nil {
		return nil, err
	}
	if invoker != req.BuyerUserID {
		return nil, errors.New("only buyer can approve")
	}
	addStatusChange(ctx, req, "BUYER_APPROVED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	return req, nil
}

func (s *SmartContract) BuyerRejectChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "SUBMITTED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	invoker, err := getInvokerID(ctx)
	if err != nil {
		return nil, err
	}
	if invoker != req.BuyerUserID {
		return nil, errors.New("only buyer can reject")
	}
	addStatusChange(ctx, req, "REJECTED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	key, _ := ctx.GetStub().CreateCompositeKey("sale", []string{req.ParcelID, req.ID})
	ctx.GetStub().DelState(key)
	return req, nil
}

func (s *SmartContract) RequesterConfirmPayment(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "BUYER_APPROVED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	invoker, err := getInvokerID(ctx)
	if err != nil {
		return nil, err
	}
	if invoker != req.RequesterUserID {
		return nil, errors.New("only requester can confirm payment")
	}
	addStatusChange(ctx, req, "PAYMENT_CONFIRMED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	return req, nil
}

func (s *SmartContract) CadastreApproveChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	if err := checkOffice(ctx, "CadastreMSP", "cadastre"); err != nil {
		return nil, err
	}
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "PAYMENT_CONFIRMED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	addStatusChange(ctx, req, "CADASTRE_APPROVED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	return req, nil
}

func (s *SmartContract) CadastreRejectChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	if err := checkOffice(ctx, "CadastreMSP", "cadastre"); err != nil {
		return nil, err
	}
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "PAYMENT_CONFIRMED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	addStatusChange(ctx, req, "REJECTED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	key, _ := ctx.GetStub().CreateCompositeKey("sale", []string{req.ParcelID, req.ID})
	ctx.GetStub().DelState(key)
	return req, nil
}

func (s *SmartContract) DistrictApproveChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	if err := checkOffice(ctx, "DistrictMSP", "district"); err != nil {
		return nil, err
	}
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "CADASTRE_APPROVED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	addStatusChange(ctx, req, "DISTRICT_APPROVED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	return req, nil
}

func (s *SmartContract) DistrictRejectChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*ChangeRequest, error) {
	if err := checkOffice(ctx, "DistrictMSP", "district"); err != nil {
		return nil, err
	}
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "CADASTRE_APPROVED" {
		return nil, fmt.Errorf("invalid status transition from %s", req.Status)
	}
	addStatusChange(ctx, req, "REJECTED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	key, _ := ctx.GetStub().CreateCompositeKey("sale", []string{req.ParcelID, req.ID})
	ctx.GetStub().DelState(key)
	return req, nil
}

func (s *SmartContract) CadastreExecuteChangeRequest(ctx contractapi.TransactionContextInterface, id string) (*Parcel, error) {
	if err := checkOffice(ctx, "CadastreMSP", "cadastre"); err != nil {
		return nil, err
	}
	req, err := s.ReadChangeRequest(ctx, id)
	if err != nil {
		return nil, err
	}
	if req.Status != "DISTRICT_APPROVED" {
		return nil, fmt.Errorf("not ready to execute (status=%s)", req.Status)
	}

	parcel, err := s.ReadParcel(ctx, req.ParcelID)
	if err != nil {
		return nil, err
	}

	locked, err := parcelHasActiveSale(ctx, req.ParcelID, req.ID)
	if err != nil {
		return nil, err
	}
	if locked {
		return nil, errors.New("parcel is locked due to an active sale")
	}

	// Apply the ownership change
	var p changePayload
	json.Unmarshal([]byte(req.ChangeJSON), &p)
	if p.Type != "TRANSFER_SHARE" {
		return nil, fmt.Errorf("unsupported change type: %s", p.Type)
	}

	// Find the seller and replace with buyer
	for i, o := range parcel.Owners {
		if o.UserID == p.FromUserID {
			parcel.Owners[i].UserID = p.ToUserID
			parcel.Owners[i].Name = p.ToName
			parcel.Owners[i].Address = p.ToAddress
			parcel.Owners[i].BirthDate = p.ToBirthDate
			break
		}
	}

	err = saveState(ctx, parcel.ID, parcel)
	if err != nil {
		return nil, err
	}

	addStatusChange(ctx, req, "EXECUTED")
	err = saveState(ctx, req.ID, req)
	if err != nil {
		return nil, err
	}
	key, _ := ctx.GetStub().CreateCompositeKey("sale", []string{req.ParcelID, req.ID})
	ctx.GetStub().DelState(key)
	return parcel, nil
}

func parcelHasActiveSale(ctx contractapi.TransactionContextInterface, parcelID string, allowedRequestID string) (bool, error) {
	iter, err := ctx.GetStub().GetStateByPartialCompositeKey("sale", []string{parcelID})
	if err != nil {
		return false, err
	}
	defer iter.Close()

	for iter.HasNext() {
		kv, err := iter.Next()
		if err != nil {
			return false, err
		}
		_, parts, _ := ctx.GetStub().SplitCompositeKey(kv.Key)
		if len(parts) == 2 && allowedRequestID != "" && parts[1] == allowedRequestID {
			continue
		}
		return true, nil
	}
	return false, nil
}
