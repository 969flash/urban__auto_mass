# -*- coding:utf-8 -*-
try:
    from typing import List, Tuple, Dict, Any, Optional, Union
except ImportError:
    pass

import Rhino.Geometry as geo  # ignore

# import fx.utils as utils
import fx.utils as utils
import random
import scriptcontext as sc

import importlib

# 모듈 새로고침
importlib.reload(utils)


def get_rails(block_regions, set_back_dist, building_depth):
    # type: (List[geo.Curve], float, float) -> List[geo.Curve]
    """
    Get rails for building(pre-skeleton of building) by offset inward of block region curves
    """
    # apply set back
    set_backed_regions = utils.offset_regions_inward(block_regions, set_back_dist)

    # offset half of buildign depth
    rails = utils.offset_regions_inward(set_backed_regions, building_depth * 0.5)

    return rails


def get_skeletons(rails, min_width, max_width, min_dist_between_buildings):
    # type: (List[geo.Curve], float, float, float) -> List[geo.Curve]
    """
    Get skeleton of buildings that length is between min width and max width.
    set width randomly
    """
    skeletons = []
    for rail in rails:
        left_rail = rail
        while utils.get_length(left_rail) > min_width:
            # get skeleton by random width
            width = random.randrange(int(min_width), int(max_width))

            # width over minnimum, but not enough for random width
            if utils.get_length(left_rail) < width:
                skeletons.append(left_rail)
                break

            skeleton = utils.trim_crv_from_length(left_rail, width)
            left_rail = utils.trim_crv_from_length(left_rail, width, reverse=True)
            skeletons.append(skeleton)

            # remove little bit of left rail for distance for next building
            if utils.get_length(left_rail) < min_dist_between_buildings:
                break
            left_rail = utils.trim_crv_from_length(
                left_rail, min_dist_between_buildings, reverse=True
            )

    return skeletons


def get_buildings(skeletons, building_depth):
    # type: (List[geo.Curve], float) -> List[geo.Curve]
    """
    Get buildings by offset skeletons
    """
    return [
        utils.offset_region_outward(skeleton, building_depth * 0.5)
        for skeleton in skeletons
    ]


def filter_buildings(buildings, block_regions, min_dist_between_buildings):
    # type: (List[geo.Curve], List[geo.Curve], float) -> List[geo.Curve]
    """
    filter bad buildings
    """
    filtered_buildings = []
    for building in buildings:
        if utils.is_intersection_with_other_crvs(
            building, block_regions + filtered_buildings
        ):
            continue

        if filtered_buildings:
            dist_to_closest_building = min(
                utils.get_dist_from_crv_crv(building, other)
                for other in filtered_buildings
            )
            if dist_to_closest_building < min_dist_between_buildings:
                continue

        filtered_buildings.append(building)

    return filtered_buildings


def extrude_buildings(buildings, min_floor, max_floor, floor_height, GFA):
    # type: (List[geo.Curve], float, float, float, float) -> List[geo.Brep]
    """
    extrude building curves to make 3d Buildings
    """

    brep_buildings = []
    total_area = 0
    for building in buildings:
        available_area = GFA - total_area
        floor_area = geo.AreaMassProperties.Compute(building).Area
        availalbe_max_floor = min(max_floor, int(available_area / floor_area))
        if availalbe_max_floor <= min_floor:
            break
        floor = random.randrange(min_floor, availalbe_max_floor)

        total_area += floor_area * floor
        height = floor_height * floor

        building_3d = geo.Extrusion.Create(building, height, cap=True)
        brep_buildings.append(building_3d)
    print(" TOTAL AREA IS " + str(total_area) + " AND GFA IS " + str(GFA))
    return brep_buildings


# input :
# reset, block_regions, set_back_dist, min_width,
# max_width, min_dist_between_buildings, min_floor,
# max_floor, floor_height, GFA, building_depth

if reset:
    raise Exception("RESET")


rails = get_rails(block_regions, set_back_dist, building_depth)

skeletons = get_skeletons(rails, min_width, max_width, min_dist_between_buildings)

buildings = get_buildings(skeletons, building_depth)

buildings = filter_buildings(buildings, block_regions, min_dist_between_buildings)

random.shuffle(buildings)


building_breps = extrude_buildings(buildings, min_floor, max_floor, floor_height, GFA)
