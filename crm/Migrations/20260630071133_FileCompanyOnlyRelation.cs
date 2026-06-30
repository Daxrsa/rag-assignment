using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace crm.Migrations
{
    /// <inheritdoc />
    public partial class FileCompanyOnlyRelation : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_app_files_app_users_AppUserId",
                table: "app_files");

            migrationBuilder.DropIndex(
                name: "IX_app_files_AppUserId",
                table: "app_files");

            migrationBuilder.DropIndex(
                name: "IX_app_files_Company",
                table: "app_files");

            migrationBuilder.DropColumn(
                name: "AppUserId",
                table: "app_files");

            migrationBuilder.DropColumn(
                name: "Company",
                table: "app_files");

            migrationBuilder.AddColumn<int>(
                name: "CompanyId",
                table: "app_files",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.CreateIndex(
                name: "IX_app_files_CompanyId",
                table: "app_files",
                column: "CompanyId");

            migrationBuilder.AddForeignKey(
                name: "FK_app_files_companies_CompanyId",
                table: "app_files",
                column: "CompanyId",
                principalTable: "companies",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_app_files_companies_CompanyId",
                table: "app_files");

            migrationBuilder.DropIndex(
                name: "IX_app_files_CompanyId",
                table: "app_files");

            migrationBuilder.DropColumn(
                name: "CompanyId",
                table: "app_files");

            migrationBuilder.AddColumn<string>(
                name: "AppUserId",
                table: "app_files",
                type: "text",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Company",
                table: "app_files",
                type: "character varying(128)",
                maxLength: 128,
                nullable: false,
                defaultValue: "");

            migrationBuilder.CreateIndex(
                name: "IX_app_files_AppUserId",
                table: "app_files",
                column: "AppUserId");

            migrationBuilder.CreateIndex(
                name: "IX_app_files_Company",
                table: "app_files",
                column: "Company");

            migrationBuilder.AddForeignKey(
                name: "FK_app_files_app_users_AppUserId",
                table: "app_files",
                column: "AppUserId",
                principalTable: "app_users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
