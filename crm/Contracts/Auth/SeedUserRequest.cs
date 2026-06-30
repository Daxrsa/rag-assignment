namespace crm.Contracts.Auth;

public sealed record SeedUserRequest(string Email, string Password, string Company, string? DisplayName);
