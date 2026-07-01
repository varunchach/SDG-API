# Schemas — Input & Output

Copy spec sample as template; change **values only**. Full nested keys live in
`EligibilityEngine_SpecDoc_SampleFiles/` — do not trim arrays or omit nulls.

---

## 1. Initiate Journey (input)

**File:** `EE- initiate request V1.0.txt`

```
contextParameter
  partnerJourneyID, bankJourneyID, partnerID, channelID, productName
  ← NO orcJourneyID

applicant
  customerSegment, perfiosCustomerSegment, mBueCustomerSegment
  customerDemog
    name[]           → fName, mName, lName
    dob, gender, age, emailId1
    address[]        → addresstype, address1..4, city, pinCode, state
    ids              → panNo
  employmentDetails  → employerName, companyCategory, companyNames
  bussinessDetails   → appId
  bankingDetails
    accountInfo[]    → customerId, formDate
    loanDetails      → loanAmount
  productDetails
    multibureau      → loanType, responseFormat
    perfios          → txnId, perfiosTransactionId
    posidex          → sourceId, productId, priority, matchingProfile, branchId
    hunter           → hunterProductPart1, hunterProductPart2

coApplicants
  totalCoApplicants, coApplicantArray[]  (same applicant shape + index)

sourceApp → constitution
```

---

## 2. ACK (sync output)

**Success:** `EE - Intiate Journey ACK resp.txt`

```
data      → orcJourneyID, bankJourneyID, partnerJourneyID, statusMessage, statusCode
messages  → codes[], requestId, keyId, overrideAuthLevelsReqd, status, httpStatusCode
```

**Failure:** `EE-Sample Failure.txt` — same shape; `statusCode`=`"1"`, error in `statusMessage`.

---

## 3. Callback envelope (all producers)

```
contextParameter   → partnerJourneyID, bankJourneyID, orcJourneyID, partnerID, channelID, productName
statusCode         → "0"
statusMsg          → "Success"
userType           → "applicant"
userIndex          → "0"
reportType         → see table below
<payload key>      → same as reportType (mbCibil, posidex, etc.)
```

| reportType | Spec file | Payload root |
|------------|-----------|--------------|
| mbCibil | mbCibil Sample Callback.txt | `mbCibil.Body.MultiBureauResponse.RESPONSE` |
| mbEquifax | mbEquifax Sample Callback.txt | `mbEquifax.Body...` + `EQUIFAX_EROP_DOMAIN_LIST[]` |
| mbHighMark | mbHighMark Sample Callback.txt | `CHM_BASE_SROP_DOMAIN_LIST[]` |
| mbMbEot | mbMbEot Sample Callback.txt | `mbMbEot.Body.MultiBureauEoTRequest` |
| perfios | perfios Sample Callback.txt | envelope + body keys below |
| posidex | posidex Sample Callback.txt | `posidex.outputdata[]` (85 fields) |
| hunter | hunter Sample Callback.txt | `hunter.Body.MatchResponse...` |
| summary | summary Sample Callback.txt | `applicant.summary` (no userType/userIndex) |

---

## 4. Producer payloads (summary)

### MultiBureau (CIBIL / Equifax / HighMark)

```
RESPONSE
  HEADER              APPLICATION-ID, CUST-ID, RESPONSE-TYPE, REQUEST-RECEIVED-TIME, SOURCE-SYSTEM
  ACKNOWLEDGEMENT-ID
  STATUS              "IN-PROCESS"
  FINISHED
    TRACKING-ID, BUREAU, PRODUCT, STATUS
    JSON-RESPONSE-OBJECT → bureau-specific domain list
    BUREAU-STRING, HTML-REPORT, PDF-REPORT
```

BUREAU values: `"CIBIL"` | `"EQUIFAX"` | `"CRIF HIGHMARK"`

### mbMbEot

`STATUS`=`"END-OF-TXN"`; `SENT-TO-CIBIL|EQUIFAX|EXPERIAN|CHM` = `"Y"`/`"N"`

### perfios (body keys — wrap with envelope)

`CustomerInfo`, `AdditionalParameters`, `Statementdetails`, `SummaryInfo`,
`MonthlyDetails`, `EODBalances`, `SalaryXns`, `FCUAnalysis`, `ScoringDetails`, `Xns`

### posidex

`outputdata[]` — all `SOA_*` and `FILLER_*` keys from sample (85 per row).

### hunter

```
MatchSummary  → matches, TotalMatchScore, Rules{ Rule[] }, MatchSchemes{ Scheme[] }
ErrorWarnings → Errors, Warnings
```

### summary

```
applicant.summary → mbCibil, mbEquifax, mbHighMark, mbEot, mbMergedScore,
                    mbExperian, mbCriflite, perfios, posidex, hunter
coApplicants      → totalCoApplicants, coApplicantArray[]{ index, summary }
```

Status values: `"Success"` | `"Failed"` | `"Late"` | `"Not Opted"`

---

## 5. Stored record (target)

```json
{
  "recordId": "CUST-0001",
  "scenario": "clean-approval",
  "initiateRequest": {},
  "ackResponse": {},
  "callbacks": {
    "mbCibil": {}, "mbEquifax": {}, "mbHighMark": {}, "mbMbEot": {},
    "perfios": {}, "posidex": {}, "hunter": {}, "summary": {}
  }
}
```

Field paths for building: [mappings.md](mappings.md). Value rules: [constraints.md](constraints.md).
