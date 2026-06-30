namespace crm.Services;

public enum ServiceError
{
    None,
    BadRequest,
    Unauthorized,
    NotFound,
    Conflict,
}

public sealed class ServiceResult<T>
{
    private ServiceResult(bool success, T? value, ServiceError error, string? message, string[]? validationErrors)
    {
        Success = success;
        Value = value;
        Error = error;
        Message = message;
        ValidationErrors = validationErrors;
    }

    public bool Success { get; }
    public T? Value { get; }
    public ServiceError Error { get; }
    public string? Message { get; }
    public string[]? ValidationErrors { get; }

    public static ServiceResult<T> Ok(T value) => new(true, value, ServiceError.None, null, null);

    public static ServiceResult<T> Fail(ServiceError error, string message)
        => new(false, default, error, message, null);

    public static ServiceResult<T> Validation(string[] errors)
        => new(false, default, ServiceError.BadRequest, "Validation failed.", errors);
}
