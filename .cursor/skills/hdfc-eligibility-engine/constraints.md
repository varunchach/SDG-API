# Field Constraints — Valid Values & Ranges

Tags: **spec** = EE sample files | **bre** = ACE BRE Generic API Spec v1.1 (PDF) | **gen** = generator rule

**Important:** ACE BRE defines the **BRE wrapper input** (`Customer journey`, `mb_cibil_srop`,
`los_input_fromsas`, `hunter_response_*`, `los_merged_*`). EE callbacks use **different JSON
names** but same semantics — use BRE for **type/length**, spec samples for **shape/enums**.
Perfios is **not** in ACE BRE PDF → **spec** only.

---

## Journey & status (spec)

| Field | Constraint | Tag |
|-------|------------|-----|
| `partnerJourneyID` | numeric string, 10–12 chars | spec |
| `bankJourneyID` | numeric string, ~11 chars | spec |
| `orcJourneyID` | `{productName}_WF_{uuid}{digits}` | spec |
| `statusCode` | `"0"` success, `"1"` failure | spec |
| `statusMsg` | `"Success"` or error text | spec |
| `reportType` | mbCibil, mbEquifax, mbHighMark, mbMbEot, perfios, posidex, hunter, summary | spec |
| summary fields | `"Success"` \| `"Failed"` \| `"Late"` \| `"Not Opted"` | spec |

---

## Customer identity

| EE field | Constraint | Tag | BRE mapping (PDF p.11–12) |
|----------|------------|-----|---------------------------|
| `panNo` / `ID_NUMBER` | `^[A-Z]{5}[0-9]{4}[A-Z]$` | gen | `pan` String **100** |
| `gender` | `"M"` \| `"F"` | spec | `gender` String **100** |
| `dob` (initiate) | `YYYY-MM-DD` | spec | `dob` Date `dd/mm/yyyy hh:mm:ss` |
| `dob` (CIBIL callback) | `DDMMYYYY` | spec | `dateofbirth` Date `dd/mm/yyyy hh:mm:ss` |
| `emailId1` | valid email | gen | `email` String **100** |
| `mobile` | 10 digits, starts 6–9 | gen | `mobile_number` String **100** |
| `fName`/`lName` | alphabetic | gen | `first_name`/`last_name` String **100** |
| `address` | free text | gen | `address` String **10,000** |
| `pinCode` | 6-digit string | gen | `pincode_1` Number **100** |
| `loanAmount` | numeric string | spec | `required_loan_amount` Number **100** |
| `customerSegment` etc. | see spec sample | spec | — |

---

## MultiBureau / CIBIL (spec + bre)

| EE / callback field | Constraint | Tag | BRE `mb_cibil_srop` (PDF p.12–18) |
|---------------------|------------|-----|-----------------------------------|
| `APPLICATION-ID`, `CUST-ID` | numeric string | spec | `proposal_no`, `cib_cust_id` String **100** |
| `MEMBER_REFERENCE_NUMBER` | numeric string | spec | `memberreferencenumber` String **100** |
| `SUBJECT_RETURN_CODE` | `"FOUND"` \| `"NOT FOUND"` | spec | `subjectreturncode` String **100** |
| `SCORE` | string e.g. `"750"`, `"-1"` | spec | `score` String **100** |
| `ID_NUMBER` | PAN format | gen | `idnumber` String **100** |
| `CONSUMER_NAME_FIELD1` | name | spec | `consumernamefield1` String **100** |
| `GENDER` | `"M"`/`"F"` | spec | `mb_gender` String **10** |
| `pincode` (address) | 6 digits | gen | `pincode` String **100** |
| `addressline1`–`5` | address parts | spec | String **200** each |
| tradeline amounts | numeric | spec/bre | `tl_disbursed_amt`, `tl_sanctioned_amt` **decimal 12,2** (p.3) |
| merged tradelines `member_reference_number` | string | bre | String **1,000** (p.3) |
| past enquiry amount | numeric | bre | `past_enq_amount` double (p.8–9) |

Equifax/HighMark callback **enums** (`BUREAU`, `STATUS`) → **spec** only.

---

## Posidex (spec + bre)

Maps to BRE `los_input_fromsas` (PDF p.5–7). EE uses `SOA_*` / `FILLER_*` names.

| EE field | Constraint | Tag | BRE field |
|----------|------------|-----|-----------|
| `FILLER_35` / PAN | PAN format | gen | `lsi_pan_c` String **1,000** |
| `SOA_FNAME_C` etc. | name strings | spec | `lsi_fname_c` String **1,000** |
| `SOA_STATUS_C` | `"Match"` \| `"No Match"` | spec | `lsi_status_c` String **1,000** |
| `SOA_MATCH_PARAMETER` | e.g. `"NAME,PAN"` | spec | — |
| loan amounts | numeric | spec/bre | `lsi_loan_amt_n` **decimal 12,2** |
| exposure | numeric | bre | `lsi_cust_exposure_n`, `lsi_total_exposure_n` **decimal 12,2** |
| `lsi_dedupe_date` | datetime | bre | Date `dd/mm/yyyy hh:mm:ss` |

All `SOA_*`, `FILLER_*` keys must exist in output (spec).

---

## Hunter (spec + bre)

Maps to `hunter_response_data` + `hunter_response_rules` (PDF p.10–11, sample JSON p.34–35).

| EE callback field | Constraint | Tag | BRE field |
|-------------------|------------|-----|-----------|
| `matches` | `"0"`–`"N"` | spec | `hrd_noofmatches` String **100** |
| `TotalMatchScore` | numeric string | spec | `hrd_totmatchscore` **Numeric** (large precision) |
| `Rule.Score` | numeric string | spec | `hrr_rulescore` **Numeric 100** (precision, not cap) |
| `RuleID` | e.g. `NH_NC_PAN` | spec | `hrr_ruleid` String **100** |
| `errorCount` | `"0"` clean | spec | `hrd_errorcount` **Numeric** |
| `hrd_match_flag` | string | bre | String **100** |

---

## Perfios (spec only — not in ACE BRE)

| Field | Constraint | Tag |
|-------|------------|-----|
| `perfiosTransactionId` | `KKH` + digits (~17) | spec |
| `txnId` | `{uuid}{digits}_applicant` | spec |
| `grade` | e.g. `"AAA"` | spec |
| `savingsBankInterestCredited` | `"true"` \| `"false"` | spec |

---

## Global BRE types (PDF)

| Type | Meaning |
|------|---------|
| String N | max N chars |
| decimal 12,2 | monetary amounts |
| Numeric N | numeric field precision N |
| Date | format `dd/mm/yyyy hh:mm:ss` |

---

## Initiate constants (spec sample)

| Field | Sample value |
|-------|--------------|
| `partnerID` | `FYNDNA` |
| `channelID` | `CHANNEL_FYNDNA_HL1` |
| `productName` | `FYNDNA_HL1` |
| `loanType` | `HOU` |
| `responseFormat` | `08` |
| `hunterProductPart1` | `HLS_I` |
| `hunterProductPart2` | `MUM` (varies) |
| `companyCategory` | `A` |

---

## Scenarios (`data/scenarios/*.json`)

File shape: `{ "name", "mbCibil":{}, "hunter":{}, ... }` — behaviour overrides only.

| Scenario | Effect |
|----------|--------|
| `clean-approval` | CIBIL FOUND score ~742, Hunter 0, Posidex no match |
| `fraud-hit` | High `TotalMatchScore`, matches ≥ 1 |
| `bureau-not-found` | Equifax `ERRORMSG` = "Consumer record not found" |
| `posidex-match` | `SOA_STATUS_C` = Match, outputdata rows ≥ 1 |
| `thin-file` | CIBIL `SCORE` = `"-1"` |

Never override `panNo`, name, or DOB from scenario files.

---

## Validation checklist

- [ ] All spec template keys present
- [ ] Identity matches initiate request across callbacks
- [ ] Journey IDs match ACK `contextParameter`
- [ ] String lengths within BRE limits where field maps
- [ ] Dates: initiate `YYYY-MM-DD`; BRE-facing `dd/mm/yyyy hh:mm:ss`; CIBIL callback `DDMMYYYY`
