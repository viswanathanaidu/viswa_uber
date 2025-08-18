USE [uber_ride]
GO
CREATE PROCEDURE sp_update_driver_location
    @driver_id INT,
    @latitude FLOAT,
    @longitude FLOAT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Update driver's current status to 'available' if offline
    UPDATE drivers 
    SET current_status = 'available'
    WHERE driver_id = @driver_id AND current_status = 'offline';
    
    -- Insert location history
    INSERT INTO driver_locations (driver_id, location)
    VALUES (@driver_id, geography::Point(@latitude, @longitude, 4326));
    
    -- Return driver's updated status
    SELECT current_status FROM drivers WHERE driver_id = @driver_id;
END;

select * from driver_locations