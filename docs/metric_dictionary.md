# Metric Dictionary

## Funnel Metrics

| Key | Label | Formula | Unit |
|-----|-------|---------|------|
| `n_applications` | Number of Applications | `COUNT(loan_id)` | count |
| `n_approved` | Number of Approved | `COUNT WHERE approved=True` | count |
| `approval_rate` | Approval Rate | `n_approved / n_applications` | % |
| `n_funded` | Number of Funded Accounts | `COUNT WHERE funded=True` | count |
| `funding_rate` | Funding Rate | `n_funded / n_approved` | % |
| `booked_balance` | Booked Balance | `SUM(loan_amnt) WHERE funded` | USD |
| `avg_funded_amount` | Average Funded Amount | `AVG(loan_amnt) WHERE funded` | USD |
| `avg_apr` | Average APR | `AVG(int_rate) WHERE funded` | % |

## Revenue Metrics

| Key | Label | Formula | Unit |
|-----|-------|---------|------|
| `interest_revenue` | Interest Revenue | `SUM(loan_amnt × int_rate × term_years × utilization)` | USD |
| `interchange_revenue` | Interchange Revenue | `SUM(loan_amnt) × 1.5%` | USD |
| `fee_revenue` | Fee Revenue | `SUM(origination_fee)` | USD |
| `late_fee_revenue` | Late Fee Revenue | `SUM(late_fees)` | USD |
| `total_revenue` | Total Revenue | `interest + interchange + fee + late_fee` | USD |
| `net_revenue` | Net Revenue | `total_revenue − actual_loss` | USD |
| `risk_adjusted_revenue` | Risk-Adjusted Revenue | `total_revenue − expected_loss` | USD |

## Loss / Delinquency Metrics

| Key | Label | Formula | Unit |
|-----|-------|---------|------|
| `dpd30_count` | 30 DPD Account Count | `COUNT WHERE dpd30=True` | count |
| `dpd30_rate` | 30 DPD Rate | `dpd30_count / n_funded` | % |
| `dpd60_count` | 60 DPD Account Count | `COUNT WHERE dpd60=True` | count |
| `dpd60_rate` | 60 DPD Rate | `dpd60_count / n_funded` | % |
| `dpd90_count` | 90 DPD Account Count | `COUNT WHERE dpd90=True` | count |
| `dpd90_rate` | 90 DPD Rate | `dpd90_count / n_funded` | % |
| `writeoff_count` | Write-Off Account Count | `COUNT WHERE charged_off=True` | count |
| `writeoff_rate` | Write-Off Rate | `writeoff_count / n_funded` | % |
| `writeoff_amount` | Write-Off Amount | `SUM(loan_amnt) WHERE charged_off` | USD |
| `writeoff_amount_rate` | Write-Off Amount Rate | `writeoff_amount / booked_balance` | % |
| `expected_loss` | Expected Loss | `SUM(pd_score × 0.60 × loan_amnt)` | USD |
| `actual_loss` | Actual Loss | `writeoff_amount × LGD` | USD |
| `loss_rate` | Loss Rate | `actual_loss / booked_balance` | % |

## Scenario Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `apr_shock_pp` | APR change in **percentage points** (additive) | 0 |
| `lgd` | Loss Given Default | 0.60 |
| `demand_sensitivity` | Volume reduction per pp APR increase | medium (5%/pp) |
| `pd_sensitivity` | PD uplift per pp APR increase | low (0.5%/pp) |

## Notes

- **APR shock is ADDITIVE.** +5pp means APR goes from 12% to 17%, NOT 12% × 1.05 = 12.6%.
- **LGD default = 60%** (industry convention for unsecured consumer loans)
- **DPD hierarchy:** 90-DPD ⊆ 60-DPD ⊆ 30-DPD (stricter buckets are subsets)
- **Write-off rate** = charged-off accounts / funded accounts (not total applications)
