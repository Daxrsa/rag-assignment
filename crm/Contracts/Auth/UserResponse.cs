namespace crm.Contracts.Auth;

public sealed record UserResponse(string Id, string? Email, string DisplayName, string Company);
