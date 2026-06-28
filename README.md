# http://127.0.0.1:1234

# Fix directions (for when you want code):

 # Decouple retrieval from the user's wording — query rewriting / HyDE: have a small LLM call rephrase the question into a neutral topic query ("employee PTO days per year") before embedding.
 # Give the prompt an explicit "correction" clause: if the user's question contains a claim that contradicts the context, state the correct value from the context and cite it.
 # Optionally lower the threshold or rerank a larger candidate set so the right chunk doesn't get filtered out for false-premise queries.

# You: can i have remote work
# Assistant:
# No. According to the context, employees are expected to be in the office a minimum of two days per week [1]. Fully remote arrangements require VP-level approval and are reviewed every six months [1].
# logically this means it's hybrid work, 3 days remote 2 days in office. The assistant should have explicity said that the company offers hybrid work.
# How can we fix this? Don't change the code yet, just tell me how to fix this:
# Why it's happening
# Look at Rule 2 in your current prompt:
# Do not infer, estimate, extrapolate, or combine facts to produce new ones. - This rule is causing the assistant to avoid making any inferences about hybrid work arrangements, even though the context implies it. 
# The assistant is strictly adhering to the rule and not providing a complete answer. This is to reduce the risk of hallucination, but in this case, it leads to an incomplete response. The assistant is not allowed to infer that "minimum of two days in the office" implies "hybrid work" because it is not explicitly stated in the context.

# Issues with the current setting: This rag chatbot is single-shot/statelss, meaing it has no memory of previous interactions. It is also not able to ask clarifying questions, so it cannot confirm the user's intent or provide a more complete answer based on cntext.
# The assistant is also not allowed to infer or combine facts, for example if you ask it "can i have remote work" and the context says "employees are expected to be in the office a minimum of two days per week", it cannot infer that this means hybrid work is allowed. It can only state what is explicitly in the context.

