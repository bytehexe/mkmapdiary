import logging
import pathlib
from threading import Lock
from typing import Any, NamedTuple

import shapely
import yaml
from shapely.geometry.base import BaseGeometry

from mkmapdiary.poi.ballTree import BallTree
from mkmapdiary.poi.ballTreeBuilder import BallTreeBuilder
from mkmapdiary.poi.common import Poi
from mkmapdiary.poi.indexBuilder import IndexBuilder, Region
from mkmapdiary.poi.indexFileReader import IndexFileReader
from mkmapdiary.poi.regionFinder import RegionFinder
from mkmapdiary.util.osm import calculate_rank, clip_rank
from mkmapdiary.util.projection import LocalProjection


class IndexKey(NamedTuple):
    regions: list[Region]
    min_rank: int
    max_rank: int


class IndexProxy:
    """
    Proxy object containing loaded regions and ball tree for POI querying.
    """

    def __init__(
        self,
        ball_tree: BallTree,
        index_key: IndexKey,
        region_data: dict[str, Any] | None = None,
    ):
        self.ball_tree = ball_tree
        self.index_key = index_key
        # Cache raw data from idx files for reuse
        self.region_data = region_data or {}

    @property
    def regions(self) -> list[Region]:
        """Get regions from the stored IndexKey."""
        return self.index_key.regions

    @property
    def min_rank(self) -> int:
        """Get minimum rank from the stored IndexKey."""
        return self.index_key.min_rank

    @property
    def max_rank(self) -> int:
        """Get maximum rank from the stored IndexKey."""
        return self.index_key.max_rank

    def get_cached_region_data(self, region_id: str) -> Any | None:
        """
        Get cached raw data for a region if available.

        Args:
            region_id: ID of the region to get data for

        Returns:
            Raw region data or None if not cached
        """
        return self.region_data.get(region_id)

    def matches_key(self, key: "IndexKey") -> bool:
        """
        Check if this proxy exactly matches the given IndexKey.

        Args:
            key: IndexKey to compare against

        Returns:
            True if regions and ranks match exactly
        """
        return self.index_key == key

    def get_nearest(self, n: int, point: shapely.Point) -> tuple[list, list[float]]:
        """
        Get the n nearest POIs to a given point.

        Args:
            n: Number of nearest neighbors to find
            point: Point to search from (defaults to center of loaded geometry)

        Returns:
            Tuple of (POI list, distances)
        """

        logger.info("Querying ball tree for nearest neighbors ...")
        logger.debug("Query point coordinates (WGS): %s", point)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query(
            [point.y, point.x],  # type: ignore
            k=n,
        )

    def get_within_radius(
        self,
        radius: float,
        point: shapely.Point,
    ) -> list[Poi]:
        """
        Get all POIs within a given radius from a point.

        Args:
            radius: Radius in meters
            point: Point to search from (defaults to center of loaded geometry)
        Returns:
            Tuple of (POI list, distances)
        """
        logger.info("Querying ball tree for points within radius ...")
        logger.debug("Query point coordinates (WGS): %s", point)
        # Convert from Shapely Point (x=lon, y=lat) to BallTree expected (lat, lon) format
        return self.ball_tree.query_radius(
            [point.y, point.x],  # type: ignore
            radius,
        )


logger = logging.getLogger(__name__)

lock = Lock()


class Index:
    def __init__(
        self,
        index_data: dict[str, Any],
        cache_dir: pathlib.Path,
        keep_pbf: bool = False,
        rank_offset: tuple[int, int] = (-1, 1),
    ):
        with lock:
            self.__init(index_data, cache_dir, keep_pbf, rank_offset)

    def __init(
        self,
        index_data: dict[str, Any],
        cache_dir: pathlib.Path,
        keep_pbf: bool,
        rank_offset: tuple[int, int],
    ) -> None:
        with open(
            pathlib.Path(__file__).parent.parent
            / "resources"
            / "poi_filter_config.yaml",
        ) as config_file:
            self.filter_config = yaml.safe_load(config_file)
            assert isinstance(self.filter_config, list), (
                "POI filter configuration should be a list.",
                self.filter_config,
            )

        # Store configuration for later use
        self.geofabrik_data = index_data
        self.cache_dir = cache_dir
        self.keep_pbf = keep_pbf
        self.rank_offset = rank_offset
        self.finder = RegionFinder(self.geofabrik_data)

    def get_key(self, geo_data: BaseGeometry) -> IndexKey:
        """
        Find the correct regions for the given geometry and return an IndexKey
        named tuple containing (regions, min_rank, max_rank).

        Args:
            geo_data: The geometry to find regions for

        Returns:
            IndexKey named tuple with regions and rank information
        """
        logger.debug("Finding matching regions for area of interest...")
        regions = self.finder.find_regions(geo_data)
        logger.info(f"Found {len(regions)} matching regions.")

        # Ensure region indices exist and are up to date
        for region in regions:
            poi_index_path = self.cache_dir / f"{region.id}.idx"

            if not poi_index_path.exists():
                logger.info(
                    f"POI index for region {region.name} does not exist. Building...",
                )
                IndexBuilder(
                    region, self.cache_dir, keep_pbf=self.keep_pbf
                ).build_index()
                continue

            region_index = IndexFileReader(poi_index_path)
            if not region_index.is_up_to_date(31536000):
                logger.info(
                    f"POI index for region {region.name} is outdated. Rebuilding...",
                )
                IndexBuilder(
                    region, self.cache_dir, keep_pbf=self.keep_pbf
                ).build_index()
                continue
            if not region_index.is_valid(self.filter_config):
                logger.info(
                    f"POI index for region {region.name} is invalid. Rebuilding...",
                )
                IndexBuilder(
                    region, self.cache_dir, keep_pbf=self.keep_pbf
                ).build_index()
                continue

            logger.info(f"Using existing POI index for region {region.name}.")

        # Calculate geometry properties for rank calculation
        logger.debug("Projecting geo data to local coordinates...")
        local_projection = LocalProjection(geo_data)
        local_geo_data = local_projection.to_local(geo_data)

        logger.debug("Calculating bounding radius...")
        if local_geo_data.area == 0:
            logger.debug(
                "Area is zero, buffering geometry by 50 meters to avoid issues...",
            )
            try:
                # Compute convex hull to simplify geometry before buffering
                # This helps avoid memory issues, otherwise buffering complex geometries can be very expensive
                local_geo_data = local_geo_data.convex_hull
            except Exception as e:
                logger.warning("Error occurred while calculating convex hull: %s", e)
            local_geo_data = local_geo_data.buffer(50, resolution=2, quad_segs=2)

        bounding_radius = shapely.minimum_bounding_radius(local_geo_data)

        logger.debug("Calculate rank for area of interest...")
        rank = calculate_rank(None, bounding_radius)
        logger.info(f"Calculated rank for the area of interest: {rank}")

        if rank is None:
            raise ValueError("Invalid rank calculated for the area of interest.")

        min_rank = clip_rank(rank + self.rank_offset[0])
        max_rank = clip_rank(rank + self.rank_offset[1])

        # Create IndexKey with all regions and calculated ranks
        key = IndexKey(regions=regions, min_rank=min_rank, max_rank=max_rank)

        logger.debug(
            f"Index key: {len(regions)} regions with ranks ({min_rank}, {max_rank})"
        )
        return key

    def load_regions(
        self,
        key: IndexKey,
        geo_data: BaseGeometry,
        existing_proxy: IndexProxy | None = None,
    ) -> IndexProxy:
        """
        Load the specified regions and build the ball tree for querying.

        Args:
            key: IndexKey tuple containing regions and rank information
            geo_data: The geometry to calculate center and bounding radius for querying
            existing_proxy: Optional existing IndexProxy to reuse regions from if they match

        Returns:
            IndexProxy containing the loaded data for querying
        """
        if not key.regions:
            raise ValueError("No regions provided in the key.")

        # Check if existing proxy matches exactly - if so, return it directly
        if existing_proxy is not None and existing_proxy.matches_key(key):
            logger.info("Reusing existing proxy with exact matching key")
            return existing_proxy

        logger.debug("Projecting geo data to local coordinates...")
        local_projection = LocalProjection(geo_data)
        local_geo_data = local_projection.to_local(geo_data)

        logger.debug("Calculating center...")

        logger.debug("Calculating bounding radius...")
        if local_geo_data.area == 0:
            logger.debug(
                "Area is zero, buffering geometry by 50 meters to avoid issues...",
            )
            try:
                # Compute convex hull to simplify geometry before buffering
                # This helps avoid memory issues, otherwise buffering complex geometries can be very expensive
                local_geo_data = local_geo_data.convex_hull
            except Exception as e:
                logger.warning("Error occurred while calculating convex hull: %s", e)
            local_geo_data = local_geo_data.buffer(50, resolution=2, quad_segs=2)

        # Build the ball tree with the specified regions and ranks
        builder = BallTreeBuilder(self.filter_config)
        region_data = {}

        for region in key.regions:
            # Check if we can reuse data from existing proxy
            cached_data = None
            if existing_proxy is not None:
                cached_data = existing_proxy.get_cached_region_data(region.id)

            if cached_data is not None:
                logger.info(f"Reusing cached data for region: {region.name}")
                data = cached_data
            else:
                logger.info(f"Loading POI index for region: {region.name}")
                # Load the index file
                poi_index_path = self.cache_dir / f"{region.id}.idx"
                reader = IndexFileReader(poi_index_path)
                data = reader.read()

            # Cache the data for future reuse
            region_data[region.id] = data
            builder.load(data, key.min_rank, key.max_rank)

        logger.debug(
            f"Index parameters: {key.regions}, ranks: ({key.min_rank}, {key.max_rank})"
        )
        logger.info("Generating ball tree ... ")
        ball_tree = builder.build()

        return IndexProxy(
            ball_tree=ball_tree,
            index_key=key,
            region_data=region_data,
        )
