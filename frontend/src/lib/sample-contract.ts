/**
 * A self-contained sample contract used by the onboarding flow ("Try a sample
 * NDA"). It is uploaded through the real `POST /api/upload` endpoint exactly
 * like a user's own file — nothing about the pipeline is stubbed. The text is
 * a synthetic mutual NDA written for this project; it deliberately contains a
 * few risk-bearing clauses (uncapped indemnity, unilateral termination, a
 * broad non-solicit, an auto-renew) so the risk radar, timeline, and agent
 * pipeline all have something to find.
 */
export const SAMPLE_CONTRACT = {
  filename: "sample-mutual-nda.txt",
  title: "Mutual Non-Disclosure Agreement",
  description:
    "A synthetic two-party NDA with a handful of intentionally risk-bearing clauses — uncapped indemnification, a unilateral termination right, a broad 24-month non-solicit, and a silent auto-renewal.",
  text: `MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement (the "Agreement") is entered into as of March 1, 2025 (the "Effective Date") by and between Northwind Analytics, Inc., a Delaware corporation with its principal place of business at 100 Harbor Street, Wilmington, Delaware ("Northwind"), and Cedar & Vale LLP, a limited liability partnership organized under the laws of New York ("Cedar & Vale"). Northwind and Cedar & Vale are each referred to as a "Party" and collectively as the "Parties."

1. PURPOSE. The Parties wish to explore a potential business relationship concerning the evaluation of contract-analysis technology (the "Purpose"). In connection with the Purpose, each Party may disclose to the other certain confidential and proprietary information.

2. DEFINITION OF CONFIDENTIAL INFORMATION. "Confidential Information" means any non-public information disclosed by one Party (the "Disclosing Party") to the other Party (the "Receiving Party"), whether orally, in writing, or by inspection of tangible objects, that is designated as confidential or that reasonably should be understood to be confidential given the nature of the information and the circumstances of disclosure. Confidential Information includes, without limitation, business plans, customer lists, pricing, financial data, source code, model weights, and the existence and terms of this Agreement.

3. EXCLUSIONS. Confidential Information does not include information that: (a) is or becomes publicly available through no fault of the Receiving Party; (b) was rightfully in the Receiving Party's possession without an obligation of confidentiality prior to disclosure; (c) is rightfully received from a third party without breach of any obligation of confidentiality; or (d) is independently developed by the Receiving Party without use of or reference to the Disclosing Party's Confidential Information.

4. OBLIGATIONS. The Receiving Party shall: (a) use the Disclosing Party's Confidential Information solely for the Purpose; (b) protect it using at least the same degree of care it uses to protect its own confidential information of like importance, and in no event less than a reasonable degree of care; and (c) not disclose it to any third party except to its employees, advisors, and contractors who have a need to know for the Purpose and who are bound by confidentiality obligations no less protective than those in this Agreement.

5. COMPELLED DISCLOSURE. If the Receiving Party is required by law, regulation, or valid court order to disclose any Confidential Information, it shall, to the extent legally permitted, give the Disclosing Party prompt written notice and reasonable assistance so that the Disclosing Party may seek a protective order.

6. TERM AND TERMINATION. This Agreement commences on the Effective Date and continues for a period of two (2) years, and shall automatically renew for successive one (1) year periods unless a Party provides notice of non-renewal. Northwind may terminate this Agreement at any time, for any reason or no reason, upon fifteen (15) days' written notice to Cedar & Vale. The confidentiality obligations in Section 4 survive termination for a period of five (5) years, and indefinitely with respect to trade secrets.

7. RETURN OF MATERIALS. Within thirty (30) days after the earlier of the completion of the Purpose or a written request from the Disclosing Party, the Receiving Party shall return or destroy all Confidential Information in its possession and, upon request, certify such destruction in writing.

8. NON-SOLICITATION. During the term of this Agreement and for twenty-four (24) months thereafter, neither Party shall, directly or indirectly, solicit for employment or hire any employee or contractor of the other Party with whom it had contact in connection with the Purpose.

9. NO LICENSE. Nothing in this Agreement grants either Party any right, title, license, or interest in the other Party's Confidential Information or intellectual property, whether by license or otherwise, except the limited right to use it for the Purpose.

10. INDEMNIFICATION. The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party and its officers, directors, employees, and agents from and against any and all losses, liabilities, damages, costs, and expenses (including reasonable attorneys' fees) arising out of or relating to the Receiving Party's breach of this Agreement. This indemnification obligation is not subject to any limitation of liability.

11. NO WARRANTY. ALL CONFIDENTIAL INFORMATION IS PROVIDED "AS IS." THE DISCLOSING PARTY MAKES NO WARRANTIES, EXPRESS OR IMPLIED, WITH RESPECT TO THE ACCURACY OR COMPLETENESS OF ANY CONFIDENTIAL INFORMATION.

12. GOVERNING LAW. This Agreement is governed by the laws of the State of Delaware, without regard to its conflict-of-laws principles. The Parties consent to the exclusive jurisdiction of the state and federal courts located in New Castle County, Delaware.

13. INJUNCTIVE RELIEF. Each Party acknowledges that a breach of this Agreement may cause irreparable harm for which monetary damages would be inadequate, and that the non-breaching Party is entitled to seek injunctive relief without the necessity of posting a bond.

14. ENTIRE AGREEMENT. This Agreement constitutes the entire agreement between the Parties concerning its subject matter and supersedes all prior or contemporaneous agreements, whether written or oral. Any amendment must be in writing and signed by both Parties.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.

NORTHWIND ANALYTICS, INC.                CEDAR & VALE LLP

By: /s/ Dana Reyes                       By: /s/ Marcus Feld
Name: Dana Reyes                         Name: Marcus Feld
Title: VP, Corporate Development         Title: Managing Partner
`,
} as const;
