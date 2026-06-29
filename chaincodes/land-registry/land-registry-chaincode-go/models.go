package main

type Owner struct {
	UserID    string `json:"userId,omitempty"`
	Name      string `json:"name"`
	Share     string `json:"share"`
	Address   string `json:"address"`
	BirthDate string `json:"birthDate"`
}

type ChangeRequest struct {
	DocType         string         `json:"docType"`
	ID              string         `json:"id"`
	ParcelID        string         `json:"parcelId"`
	RequesterUserID string         `json:"requesterUserId"`
	BuyerUserID     string         `json:"buyerUserId,omitempty"`
	ChangeJSON      string         `json:"changeJson"`
	Status          string         `json:"status"`
	StatusHistory   []StatusChange `json:"statusHistory,omitempty"`
}

type StatusChange struct {
	FromStatus string `json:"fromStatus"`
	ToStatus   string `json:"toStatus"`
	ByUserID   string `json:"byUserId"`
	ByUserName string `json:"byUserName"`
	At         string `json:"at"`
	TxID       string `json:"txId,omitempty"`
}

type Point struct {
	X int `json:"x"`
	Y int `json:"y"`
}

type Parcel struct {
	DocType                   string  `json:"docType"`
	ID                        string  `json:"id"`
	ParcelID                  string  `json:"parcelId"`
	ParcelNumber              string  `json:"parcelNumber"`
	ListOwnershipNumber       int     `json:"listOwnershipNumber"`
	CadastralArea             string  `json:"cadastralArea"`
	Area                      int     `json:"area"`
	LandType                  string  `json:"landType"`
	UsageMethodCode           int     `json:"usageMethodCode"`
	ProtectedPropertyTypeCode int     `json:"protectedPropertyTypeCode"`
	IsCommonProperty          bool    `json:"isCommonProperty"`
	Location                  string  `json:"location"`
	LegalRelationshipTypeCode int     `json:"legalRelationshipTypeCode"`
	Owners                    []Owner `json:"owners"`
	Burdens                   string  `json:"burdens"`
	Points                    []Point `json:"points"`
}

type changePayload struct {
	Type        string `json:"type"`
	FromUserID  string `json:"fromUserId"`
	ToUserID    string `json:"toUserId"`
	ToName      string `json:"toName,omitempty"`
	ToAddress   string `json:"toAddress,omitempty"`
	ToBirthDate string `json:"toBirthDate,omitempty"`
	Share       string `json:"share"`
}
