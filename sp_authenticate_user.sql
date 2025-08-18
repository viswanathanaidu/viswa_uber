
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_authenticate_user')
DROP PROCEDURE sp_authenticate_user
GO

CREATE PROCEDURE sp_authenticate_user
    @email NVARCHAR(255),
    @password_hash NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Check if user exists with matching credentials
        SELECT 
            u.user_id,
            u.email,
            u.first_name,
            u.last_name,
            u.account_status,
            u.user_type,
            CASE 
                WHEN u.user_type = 'rider' THEN r.wallet_balance
                ELSE NULL
            END AS wallet_balance,
            CASE 
                WHEN u.user_type = 'driver' THEN d.is_verified
                ELSE NULL
            END AS is_verified,
            CASE 
                WHEN u.user_type = 'driver' THEN d.current_status
                ELSE NULL
            END AS driver_status,
            CASE 
                WHEN u.user_type = 'driver' THEN v.vehicle_id
                ELSE NULL
            END AS vehicle_id
        FROM 
            users u
            LEFT JOIN riders r ON u.user_id = r.rider_id
            LEFT JOIN drivers d ON u.user_id = d.driver_id
            LEFT JOIN vehicles v ON d.driver_id = v.driver_id
        WHERE 
            u.email = @email 
            AND u.password_hash = @password_hash
            AND u.account_status = 'active';
            
        IF @@ROWCOUNT = 0
        BEGIN
            -- No user found with these credentials
            RETURN 1
        END
    END TRY
    BEGIN CATCH
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
        RETURN -1;
    END CATCH
END
GO