'use strict';

const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const http = require('http');
const constants = require('./config/constants.json');

const host = process.env.HOST || constants.host;
const port = process.env.PORT || constants.port;
const defaultOrgName = process.env.FABRIC_ORG || constants.defaultOrgName;
const defaultUsername = process.env.FABRIC_USERNAME || constants.defaultUsername;

const helper = require('./app/helper');
const invoke = require('./app/invoke');
const query = require('./app/query');

const app = express();
app.use(cors());
app.use(bodyParser.json());

var server = http.createServer(app).listen(port, host, function () {
    console.log('Server started on %s:%s', host, port);
});
server.timeout = 240000;

app.get('/health', function (req, res) {
    res.json({ ok: true });
});

app.post('/users', async function (req, res) {
    try {
        const { username, orgName, attrs } = req.body;
        if (!username || !orgName) {
            return res.json({ success: false, message: 'username and orgName are required' });
        }
        const result = await helper.registerAndEnrollUser(username, orgName, attrs);
        return res.json(result);
    } catch (e) {
        return res.status(500).json({ success: false, message: e.message });
    }
});

app.post('/users/login', async function (req, res) {
    try {
        const { username, orgName } = req.body;
        if (!username || !orgName) {
            return res.json({ success: false, message: 'username and orgName are required' });
        }
        const ok = await helper.isUserRegistered(username, orgName);
        return res.json({ success: ok });
    } catch (e) {
        return res.status(500).json({ success: false, message: e.message });
    }
});

app.post('/channels/:channelName/chaincodes/:chaincodeName', async function (req, res) {
    try {
        const { channelName, chaincodeName } = req.params;
        const { fcn, args, transientData, transient } = req.body;
        const username = req.header('x-fabric-username') || defaultUsername;
        const orgName = req.header('x-fabric-org') || defaultOrgName;

        if (!fcn || !args) {
            return res.json({ result: null, error: 'fcn and args are required' });
        }

        const message = await invoke.invokeTransaction(channelName, chaincodeName, fcn, args, username, orgName, transientData ?? transient);
        res.json({ result: message, error: null, errorData: null });
    } catch (error) {
        res.json({ result: null, error: error.name, errorData: error.message });
    }
});

app.get('/channels/:channelName/chaincodes/:chaincodeName', async function (req, res) {
    try {
        const { channelName, chaincodeName } = req.params;
        let args = req.query.args;
        const fcn = req.query.fcn;
        const username = req.header('x-fabric-username') || defaultUsername;
        const orgName = req.header('x-fabric-org') || defaultOrgName;

        if (!fcn || !args) {
            return res.json({ result: null, error: 'fcn and args are required' });
        }

        args = args.replace(/'/g, '"');
        args = JSON.parse(args);

        const message = await query.query(channelName, chaincodeName, args, fcn, username, orgName);
        res.json({ result: message, error: null, errorData: null });
    } catch (error) {
        res.json({ result: null, error: error.name, errorData: error.message });
    }
});
