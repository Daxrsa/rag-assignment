namespace crm.Contracts.Auth;

public sealed record RetrievalMetadataFilter(int company_id);

public sealed record AllowedDocumentResponse(int Id, string FileName);

public sealed record AccessPolicyResponse(
    int CompanyId,
    string Company,
    IReadOnlyList<string> Roles,
    IReadOnlyList<AllowedDocumentResponse> AllowedDocuments,
    string TenantIndexName,
    RetrievalMetadataFilter MetadataFilter);