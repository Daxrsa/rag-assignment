using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace crm.Migrations
{
    /// <inheritdoc />
    public partial class CompanyCascadeDelete : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_app_users_companies_CompanyId",
                table: "app_users");

            migrationBuilder.AddForeignKey(
                name: "FK_app_users_companies_CompanyId",
                table: "app_users",
                column: "CompanyId",
                principalTable: "companies",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_app_users_companies_CompanyId",
                table: "app_users");

            migrationBuilder.AddForeignKey(
                name: "FK_app_users_companies_CompanyId",
                table: "app_users",
                column: "CompanyId",
                principalTable: "companies",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);
        }
    }
}
