CREATE PROCEDURE sp_register_user
    @email NVARCHAR(255),
    @phone_number NVARCHAR(20),
    @password_hash NVARCHAR(255),
    @first_name NVARCHAR(100),
    @last_name NVARCHAR(100),
    @date_of_birth DATE = NULL,
    @profile_picture_url NVARCHAR(255) = NULL,
    @account_status VARCHAR(20) = 'active',
    @user_type VARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Check if email or phone already exists
        IF EXISTS (SELECT 1 FROM users WHERE email = @email OR phone_number = @phone_number)
        BEGIN
            RAISERROR('Email or phone number already registered', 16, 1);
        END
        
        -- Insert user
        INSERT INTO users (
            email, phone_number, password_hash, first_name, last_name,
            date_of_birth, profile_picture_url, account_status, user_type
        )
        VALUES (
            @email, @phone_number, @password_hash, @first_name, @last_name,
            @date_of_birth, @profile_picture_url, @account_status, @user_type
        );
        
        DECLARE @user_id INT = SCOPE_IDENTITY();
        
        -- Create rider/driver specific record
        IF @user_type = 'rider'
        BEGIN
            INSERT INTO riders (rider_id, wallet_balance)
            VALUES (@user_id, 0.00);
        END
        ELSE IF @user_type = 'driver'
        BEGIN
            INSERT INTO drivers (driver_id, is_verified, average_rating, total_trips, current_status)
            VALUES (@user_id, 0, 0.00, 0, 'offline');
        END
        
        COMMIT TRANSACTION;
        
        -- Return the created user
        SELECT * FROM users WHERE user_id = @user_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        THROW;
    END CATCH
END;