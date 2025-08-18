USE uber_ride;
GO

IF OBJECT_ID('sp_update_user_profile', 'P') IS NOT NULL
    DROP PROCEDURE sp_update_user_profile;
GO

CREATE PROCEDURE sp_update_user_profile
    @user_id INT,
    @email NVARCHAR(255) = NULL,
    @phone_number NVARCHAR(20) = NULL,
    @first_name NVARCHAR(100) = NULL,
    @last_name NVARCHAR(100) = NULL,
    @profile_picture_url NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Check if user exists
    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = @user_id)
    BEGIN
        RAISERROR('User not found', 16, 1);
        RETURN;
    END

    -- Update fields only if they are provided (NULL means keep old value)
    UPDATE users
    SET 
        email = COALESCE(@email, email),
        phone_number = COALESCE(@phone_number, phone_number),
        first_name = COALESCE(@first_name, first_name),
        last_name = COALESCE(@last_name, last_name),
        profile_picture_url = COALESCE(@profile_picture_url, profile_picture_url),
        updated_at = GETDATE()
    WHERE user_id = @user_id;

    -- Return updated user
    SELECT 
        user_id,
        email,
        phone_number,
        first_name,
        last_name,
        profile_picture_url,
        account_status,
        created_at,
        updated_at
    FROM users
    WHERE user_id = @user_id;
END;
GO
