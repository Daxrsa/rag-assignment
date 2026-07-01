using crm.Contracts.Auth;

namespace crm.Contracts.Retrieval;

public sealed record RetrievalResponse(
    string SessionId,
    string Answer,
    double TopScore,
    AccessPolicyResponse AccessPolicy);