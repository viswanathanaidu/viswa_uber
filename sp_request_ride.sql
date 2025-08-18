USE [uber_ride]
GO

IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_request_ride')
DROP PROCEDURE sp_request_ride
GO

CREATE PROCEDURE sp_request_ride
    @rider_id INT,
    @pickup_lat FLOAT,
    @pickup_lng FLOAT,
    @dropoff_lat FLOAT,
    @dropoff_lng FLOAT,
    @pickup_address NVARCHAR(MAX),
    @dropoff_address NVARCHAR(MAX),
    @ride_type VARCHAR(20) = 'standard'
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Check rider exists and is active
        IF NOT EXISTS (
            SELECT 1 FROM users u
            JOIN riders r ON u.user_id = r.rider_id
            WHERE u.user_id = @rider_id 
            AND u.account_status = 'active'
        )
        BEGIN
            RAISERROR('Invalid or inactive rider', 16, 1);
        END
        
        -- Create ride record
        DECLARE @pickup_geo GEOGRAPHY = GEOGRAPHY::Point(@pickup_lat, @pickup_lng, 4326);
        DECLARE @dropoff_geo GEOGRAPHY = GEOGRAPHY::Point(@dropoff_lat, @dropoff_lng, 4326);
        
        INSERT INTO rides (
            rider_id, pickup_location, dropoff_location,
            pickup_address, dropoff_address, ride_type,
            ride_status, requested_at
        )
        VALUES (
            @rider_id, @pickup_geo, @dropoff_geo,
            @pickup_address, @dropoff_address, @ride_type,
            'requested', GETDATE()
        );
        
        DECLARE @ride_id INT = SCOPE_IDENTITY();
        DECLARE @distance_km DECIMAL(5,2) = @pickup_geo.STDistance(@dropoff_geo) / 1000;
        DECLARE @base_fare DECIMAL(10,2);
        DECLARE @per_km_rate DECIMAL(10,2);
        DECLARE @estimated_fare DECIMAL(10,2);
        DECLARE @surge_multiplier DECIMAL(3,2) = 1.00;
        
        -- Get pricing based on ride type
        IF @ride_type = 'standard'
        BEGIN
            SET @base_fare = 30.00;
            SET @per_km_rate = 12.00;
        END
        ELSE IF @ride_type = 'premium'
        BEGIN
            SET @base_fare = 50.00;
            SET @per_km_rate = 18.00;
        END
        ELSE IF @ride_type = 'pool'
        BEGIN
            SET @base_fare = 20.00;
            SET @per_km_rate = 8.00;
        END
        
        SET @estimated_fare = @base_fare + (@distance_km * @per_km_rate);
        
        -- Apply surge pricing if needed
        DECLARE @active_rides_in_area INT;
        
        SELECT @active_rides_in_area = COUNT(*) 
        FROM rides 
        WHERE ride_status IN ('requested', 'accepted', 'arrived', 'in_progress')
        AND pickup_location.STDistance(@pickup_geo) < 5000; -- 5km radius
        
        IF @active_rides_in_area > 50
            SET @surge_multiplier = 1.50;
        ELSE IF @active_rides_in_area > 30
            SET @surge_multiplier = 1.25;
            
        SET @estimated_fare = @estimated_fare * @surge_multiplier;
        
        -- Update ride with fare estimate
        UPDATE rides
        SET 
            estimated_fare = @estimated_fare,
            distance_km = @distance_km,
            surge_multiplier = @surge_multiplier
        WHERE ride_id = @ride_id;
        
        -- Return the created ride details with converted coordinates
        SELECT 
            ride_id,
            rider_id,
            driver_id,
            vehicle_id,
            pickup_location.Lat AS pickup_lat,
            pickup_location.Long AS pickup_lng,
            dropoff_location.Lat AS dropoff_lat,
            dropoff_location.Long AS dropoff_lng,
            pickup_address,
            dropoff_address,
            ride_status,
            ride_type,
            requested_at,
            accepted_at,
            started_at,
            completed_at,
            estimated_fare,
            actual_fare,
            distance_km,
            duration_minutes,
            surge_multiplier,
            payment_status
        FROM rides 
        WHERE ride_id = @ride_id;
        
        -- Find nearby available drivers (within 5km)
        SELECT 
            d.driver_id,
            u.first_name + ' ' + u.last_name AS driver_name,
            v.vehicle_make + ' ' + v.vehicle_model AS vehicle,
            v.vehicle_number,
            dl.location.STDistance(@pickup_geo) / 1000 AS distance_km,
            d.average_rating,
            @estimated_fare AS estimated_fare,
            @ride_id AS ride_id
        FROM drivers d
        JOIN users u ON d.driver_id = u.user_id
        JOIN vehicles v ON d.driver_id = v.driver_id
        JOIN (
            SELECT driver_id, location
            FROM driver_locations dl1
            WHERE recorded_at = (
                SELECT MAX(recorded_at) 
                FROM driver_locations dl2
                WHERE dl2.driver_id = dl1.driver_id
            )
        ) dl ON d.driver_id = dl.driver_id
        WHERE d.current_status = 'available' 
        AND d.is_verified = 1
        AND dl.location.STDistance(@pickup_geo) < 5000
        ORDER BY dl.location.STDistance(@pickup_geo);
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END
GO