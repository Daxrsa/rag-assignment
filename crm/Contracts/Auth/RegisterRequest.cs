namespace crm.Contracts.Auth;

public sealed record RegisterRequest(string Email, string Password, string Company, string? DisplayName);
