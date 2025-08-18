CREATE PROCEDURE sp_accept_ride
    @ride_id INT,
    @driver_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Check ride status
        DECLARE @current_status VARCHAR(20);
        DECLARE @rider_id INT;
        
        SELECT 
            @current_status = ride_status,
            @rider_id = rider_id
        FROM rides
        WHERE ride_id = @ride_id;
        
        IF @current_status IS NULL
        BEGIN
            RAISERROR('Ride not found', 16, 1);
        END
        
        IF @current_status != 'requested'
        BEGIN
            RAISERROR('Ride is not in requested state', 16, 1);
        END
        
        -- Check driver availability
        IF NOT EXISTS (
            SELECT 1 FROM drivers 
            WHERE driver_id = @driver_id 
            AND current_status = 'available'
            AND is_verified = 1
        )
        BEGIN
            RAISERROR('Driver not available or not verified', 16, 1);
        END
        
        -- Get driver's primary vehicle
        DECLARE @vehicle_id INT;
        
        SELECT @vehicle_id = vehicle_id
        FROM vehicles
        WHERE driver_id = @driver_id;
        
        IF @vehicle_id IS NULL
        BEGIN
            RAISERROR('Driver has no registered vehicle', 16, 1);
        END
        
        -- Update ride and driver status
        UPDATE rides
        SET 
            driver_id = @driver_id,
            vehicle_id = @vehicle_id,
            ride_status = 'accepted',
            accepted_at = GETDATE()
        WHERE ride_id = @ride_id;
        
        UPDATE drivers
        SET current_status = 'on_ride'
        WHERE driver_id = @driver_id;
        
        -- Return updated ride details
        SELECT 
            r.*,
            u.first_name + ' ' + u.last_name AS rider_name,
            u.phone_number AS rider_phone,
            pickup_location.Lat AS pickup_lat,
            pickup_location.Long AS pickup_lng,
            dropoff_location.Lat AS dropoff_lat,
            dropoff_location.Long AS dropoff_lng
        FROM rides r
        JOIN users u ON r.rider_id = u.user_id
        WHERE r.ride_id = @ride_id;
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        THROW;
    END CATCH
END;

select * from users
select * from vehicles
select * from driver_documents 
