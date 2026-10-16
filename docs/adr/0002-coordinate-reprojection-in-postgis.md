---
id: ADR-0002
date: 2026-10-16
author: Tyler Kelsey
title: Send raw coordinates with EPSG code, reproject in PostGIS
---

# ADR-0002 – Send raw coordinates with EPSG code, reproject in PostGIS

## Context

Borehole logs give coordinates in different systems: geographic, UTM and Gauss-Krüger, among others (the `CoordinateSystem` field in the borehole data format). The global geodatabase needs one common system. Many logs have no coordinates at all.

## Decision

The pipeline sends the coordinates **as written in the source**, plus an EPSG code for the system they're in. The API stores the raw values and builds the geometry with `ST_Transform(ST_SetSRID(ST_MakePoint(x, y), epsg), 4326)`. The geometry column can be null, because boreholes without coordinates are still stored.

## Pros

- The Python side needs no projection library (pyproj).
- The original values are kept, so reprojection can be redone if the EPSG code turns out to be wrong.
- PostGIS reprojection is well tested.

## Cons

- The extraction step still has to work out the right EPSG code (for example the UTM zone), and that is the error-prone part.
- If the EPSG code is wrong, the borehole is silently placed in the wrong spot.

## Alternatives

- Reproject in Python with pyproj before sending: adds a dependency and drops the raw values unless we also send them.

## Consequences

- The borehole table has columns for the raw X/Y, the EPSG code and a nullable `geometry(Point, 4326)`.
- The API handles a borehole with no coordinates or no EPSG code by storing a null geometry.

## References

- ADR-0001
- PostGIS `ST_Transform`
