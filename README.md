# Outline of my design decisions for improving the RAG system:

1-----------------------------------------------------------------------------------------------------
The reason behind using a second LLM call for rewritting user questions is done to improve 
retrieval by aligning user phasing with document wording so embedding search finds the right chunks.
This does not change what the user asked, it only improves the phasing so the LLM gets better context.

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
Add notes about where the system fails and why