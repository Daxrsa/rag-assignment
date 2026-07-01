namespace crm.Contracts.Files;

public sealed record RetrievalDocumentResponse(int Id, string FileName, string Content, int CompanyId);