# Field Mappings — Generator → Spec JSON

Maps internal generator output (`profile`, `journey`, `systemIds`) to exact spec field paths.

---

## Initiate request (`initiateRequest`)

| Internal (`profile` / `journey`) | Spec path |
|----------------------------------|-----------|
| `journey.partnerJourneyID` | `contextParameter.partnerJourneyID` |
| `journey.bankJourneyID` | `contextParameter.bankJourneyID` |
| `journey.partnerID` | `contextParameter.partnerID` |
| `journey.channelID` | `contextParameter.channelID` |
| `journey.productName` | `contextParameter.productName` |
| — | `contextParameter.orcJourneyID` **omit** (added in ACK only) |
| `profile.firstName` | `applicant.customerDemog.name[0].fName` |
| `profile.middleName` | `applicant.customerDemog.name[0].mName` |
| `profile.lastName` | `applicant.customerDemog.name[0].lName` |
| `profile.dob` | `applicant.customerDemog.dob` |
| `profile.gender` | `applicant.customerDemog.gender` |
| `profile.age` | `applicant.customerDemog.age` |
| `profile.email` | `applicant.customerDemog.emailId1` |
| `profile.addressType` | `applicant.customerDemog.address[0].addresstype` |
| `profile.addressLine1`–`4` | `address1`–`address4` |
| `profile.city` / `state` / `pinCode` | same keys |
| `profile.pan` | `applicant.customerDemog.ids.panNo` |
| `profile.employerName` | `applicant.employmentDetails.employerName` |
| `profile.loanAmount` | `applicant.bankingDetails.loanDetails.loanAmount` |
| `profile.customerId` | `applicant.bankingDetails.accountInfo[0].customerId` |
| `journey.productDetails.*` | `applicant.productDetails.*` |
| fixed | `customerSegment`=`INDIVIDUAL`, `perfiosCustomerSegment`=`RETAIL`, `mBueCustomerSegment`=`Individual` |
| fixed | `employmentDetails.companyCategory`=`A` |
| fixed | `sourceApp.constitution` per sample |

**DOB transforms:** initiate `YYYY-MM-DD` → CIBIL callback `DDMMYYYY` (strip hyphens, reorder).

---

## ACK (`ackResponse`)

| Source | Spec path |
|--------|-----------|
| `journey.orcJourneyID` | `data.orcJourneyID` |
| `journey.bankJourneyID` | `data.bankJourneyID` |
| `journey.partnerJourneyID` | `data.partnerJourneyID` |
| fixed success | `data.statusCode`=`"0"`, `data.statusMessage`=`"Success"` |
| generated UUID | `messages.requestId` |
| fixed | `messages.status`=`"SUCCESS"`, `messages.httpStatusCode`=`"200"` |

Failure variant: `EE-Sample Failure.txt` — `statusCode`=`"1"`, error message in `statusMessage`.

---

## Callback envelope (all producers)

| Source | Path |
|--------|------|
| `journey.*` | `contextParameter.*` (includes `orcJourneyID`) |
| fixed | `statusCode`=`"0"`, `statusMsg`=`"Success"` |
| fixed | `userType`=`"applicant"`, `userIndex`=`"0"` |
| key name | `reportType` = mbCibil, mbEquifax, etc. |

---

## Producer payload paths

### Shared context
`contextParameter.{partnerJourneyID,bankJourneyID,orcJourneyID,partnerID,channelID,productName}`

### mbCibil / mbEquifax / mbHighMark
| Internal | Callback path |
|----------|---------------|
| `systemIds.multibureau.applicationId` | `*.HEADER.APPLICATION-ID` |
| `systemIds.multibureau.custId` | `*.HEADER.CUST-ID` |
| `systemIds.multibureau.acknowledgementId` | `ACKNOWLEDGEMENT-ID` |
| `systemIds.multibureau.mbCibil.trackingId` (per bureau) | `FINISHED.TRACKING-ID` |
| `profile.pan` | CIBIL: `CIBIL_SROP_DOMAIN_LIST[0].ID_NUMBER`; HighMark: `PAN_IQ` |
| `profile.fullName` | `CONSUMER_NAME_FIELD1` |
| `profile.dob` | CIBIL `DATE_OF_BIRTH` (DDMMYYYY) |
| `profile.gender` | `GENDER` |
| scenario | `SCORE`, `SUBJECT_RETURN_CODE`, Equifax `ERRORMSG` |

### mbMbEot
`systemIds.multibureau.*` for HEADER/ACK; `STATUS`=`"END-OF-TXN"`; `SENT-TO-*` flags.

### perfios
| Internal | Path (inside `perfios` key after envelope) |
|----------|---------------------------------------------|
| `profile.pan` | `CustomerInfo.pan` |
| `profile.fullName` | `CustomerInfo.name` |
| `profile.email` / `mobile` | `CustomerInfo.email` / `mobile` |
| `journey.productDetails.perfios.perfiosTransactionId` | `CustomerInfo.perfiosTransactionId` |
| `profile.employerName` | `AdditionalParameters.employerName` |
| scenario | `ScoringDetails.grade`, `SummaryInfo.medianSalary` |

Note: spec sample is raw body — **wrap** with envelope + `reportType`:`"perfios"`.

### posidex
| Internal | `posidex.outputdata[0].*` |
|----------|---------------------------|
| `systemIds.posidex.soaAppId` | `SOA_APP_ID_C` |
| `profile.pan` | `FILLER_35` |
| `profile.firstName` / `lastName` | `SOA_FNAME_C` / `SOA_LNAME_C` |
| `systemIds.posidex.soaMatchAppId` | `SOA_MATCH_APPID_C` |
| scenario | `SOA_STATUS_C`, row count |

### hunter
| Internal | Path |
|----------|------|
| scenario | `MatchSummary.matches`, `TotalMatchScore`, `Rules.Rule[]` |

### summary
Derive `applicant.summary.{mbCibil,mbEquifax,...}` from each callback outcome.
Systems not in input `productDetails` → `"Not Opted"`.
