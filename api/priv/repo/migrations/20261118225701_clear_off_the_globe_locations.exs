defmodule Api.Repo.Migrations.ClearOffTheGlobeLocations do
  use Ecto.Migration

  # Before the API refused them, x/y in another system than their EPSG (e.g. UTM metres stored as
  # 4326) could land off the globe and break the map. Clear those locations and flag them for
  # review; source_x/source_y/source_epsg stay, so only the EPSG needs fixing.
  def up do
    execute("""
    INSERT INTO field_flags (id, borehole_id, field, severity, origin, code, message, inserted_at, updated_at)
    SELECT gen_random_uuid(), id, 'location', 'error', 'rule', 'location_off_the_globe',
           'The stored x/y do not fit their EPSG code (the point lies off the globe); probably another coordinate system',
           now(), now()
    FROM boreholes
    WHERE location IS NOT NULL
      AND (abs(ST_X(location)) > 180 OR abs(ST_Y(location)) > 90)
    """)

    execute("""
    UPDATE boreholes SET location = NULL
    WHERE location IS NOT NULL
      AND (abs(ST_X(location)) > 180 OR abs(ST_Y(location)) > 90)
    """)
  end

  def down, do: :ok
end
