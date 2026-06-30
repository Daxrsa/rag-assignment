namespace crm.Contracts.Files;

public sealed record FileResponse(int Id, string FileName, string Company, DateTime CreatedAtUtc);
