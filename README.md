# Outline of my design decisions for improving the RAG system:

1-----------------------------------------------------------------------------------------------------
The reason behind using a second LLM call for rewritting user questions is done to improve 
retrieval by aligning user phasing with document wording so embedding search finds the right chunks.
This does not change what the user asked, it only improves the phasing so the LLM gets better context.
I tested cases with and without it and found the model answered better and more often.

2-----------------------------------------------------------------------------------------------------
The normal threshold at 0.30 (SIMILARITY_THRESHOLD=0.30)
The second, softer threshold of 0.25 (SIMILARITY_THRESHOLD_TOP1=0.25)

How they work together:
- We retrieve the top K scored chunks normally
- We keep all chunks with score >= 0.30 
- If none pass 0.30, check only the best chunk,
     - If top-1 (best) chunk is >=0.25, we keep it
     - otherwise we keep nothing and return refusal

How this helps: 
- It helps when we ask questions using phasing that's not present in the documents but has the same meaning. 
- The cost is that this requires a second LLM call but helps in improving answers.

3-----------------------------------------------------------------------------------------------------
Verifying the accuracy and correctness of answers:
We verify answers by using another LLM call. The RAG pattern is:
1. Query rewrite (with domain phasing)
2. Answer generation
3. Answer-grounding verification
The problem with this approach is the higher cost and latency, cause we're paying for triple the calls. In order to mend this, we will use the (3.) LLM call only when mistakes are high impact (low retrieval confidence - more likely to hallucinate, asking about policy, finance, legality etc), rather than low impact (asking about notes, Q&A etc). How do we differential between high impact and low impact? 
- High impact verification: the model has low retrieval confidence (weak top-k similarity and sparse overlap), the user question is long and multi-part, answer includes numbers, dates, policy/legal claims, model provides uncertain or mixed evidence across chunks and/or no clear citations are attached to each claim.

4-----------------------------------------------------------------------------------------------------
Evaluation cases:

python -m evals.run_eval

These are the results of one run (they vary between 80%-93% based on the run). 

Aggregate: 13/15 passed (87%)
By category:
  ambiguous          2/2
  factual            6/8
  false_premise      1/1
  meta               1/1
  out_of_scope       3/3

Failed cases:
- One case failed because even though the model retrieved only one chunk, the answer was close but the grader expected a more specific phase match. This is mostly a generation/wording problem on top of a thin retrieval context.
- The second failure happened because retrieval was weak (top=0.270) and only one chunk survived, when two were needed for the right answer.

5-----------------------------------------------------------------------------------------------------
Multi-tenant document isolation:

Pre-tenant indexes
Every chunk is tagged with a company_id. This is done during the ingestion phase so ownership remains immutable metada, not inferred later. Then, every vector search must include a hard metadata filter like company_id, to ensure that the model can answer the user only questions regarding their company's documents.
- We build an access policy object (company, roles, allowed documents)
- Before retrieval, the logged in user's token is checked to resolve their identity. 
- The policy is applied vector retrieval.
- Indexes are logically isolated by having one per tenant/company.

Optional:
We can created caches for questions that are frequently asked, like "what is our PTO policy?" We do this by generating a question_hash and saving it in cache. But, this means that when two different tenants ask the same question, they could both receive the same answer, causing data leak. Solution: Isolate caches by tenant so cached chunks cannot leak across tenants. Each cache must include a tenant ID.

What happens when documents are updated or deleted? We implement a mechanism in the backend to wipe stale cache data.

What if the document is a Google Docs being edited in real-time? (MCP server for fetching document, some kind of real-time indicator that the document is being edited so the user knows that the information could change at any time, fetch google docs history, etc)