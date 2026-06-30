namespace crm.Models;

public class Company
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public ICollection<AppUser> Users { get; set; } = new List<AppUser>();
    public ICollection<AppFile> Files { get; set; } = new List<AppFile>();
}
