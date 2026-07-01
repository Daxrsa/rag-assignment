namespace crm.Contracts.Retrieval;

public sealed record RetrievalRequest(
    string Message,
    string? SessionId,
    IReadOnlyList<int>? DocumentIds);