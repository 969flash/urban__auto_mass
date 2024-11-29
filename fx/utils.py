# -*- coding:utf-8 -*-
try:
    from typing import List, Tuple, Dict, Any, Optional, Union
except ImportError:
    pass
import collections
from operator import attrgetter
import functools

import Rhino
import Rhino.Geometry as geo  # ignore
import ghpythonlib.components as ghcomp  # ignore

BIGNUM = 10000000

TOL = 0.001
DIST_TOL = 0.01
AREA_TOL = 0.1
OP_TOL = 0.00001
CLIPPER_TOL = 0.0000000001


def trim_crv_from_length(crv, length, reverse=False):
    # type: (geo.Curve, float, bool) -> geo.Curve
    """crv의 시작점부터 lenth까지의 커브를 구한다."""
    is_len_possible, param = crv.LengthParameter(length)
    if not is_len_possible:
        return crv

    ## for Rhino 8, REMOVE FOR RHINO7 !!!##
    param = float(param)
    ########################################

    if reverse:
        return crv.Trim(param, crv.Domain.Max)
    return crv.Trim(0.0, param)


def trim_crv_from_length(crv, length, reverse=False):
    # type: (geo.Curve, float, bool) -> geo.Curve
    """crv의 시작점부터 lenth까지의 커브를 구한다."""
    is_len_possible, param = crv.LengthParameter(length)
    if not is_len_possible:
        return crv

    ## for Rhino 8, REMOVE FOR RHINO7 !!!##
    param = float(param)
    ########################################

    if reverse:
        return crv.Trim(param, crv.Domain.Max)
    return crv.Trim(0.0, param)


def get_length(crvs, ndigits=3):
    # type: (List[geo.Curve], int) -> float
    if not isinstance(crvs, list):
        return round(crvs.GetLength(), ndigits)
    length = 0
    for crv in crvs:
        length += round(crv.GetLength(), ndigits)
    return length


def get_dist_from_crv_crv(crv_a, crv_b):
    # type: (geo.Curve, geo.Curve) -> float
    """두 커브 사이의 거리를 잰다.

    Args:
        crv_a : crv_b과 거리를 잴 커브
        crv_b : crv_a과 거리를 잴 커브

    Returns:
        두 커브 사이 거리
    """
    _, a, b = crv_a.ClosestPoints(crv_b)
    dist = a.DistanceTo(b)
    dist = round(dist, 6)
    return dist


def is_intersection_with_other_crvs(crv, crvs):
    # type: (geo.Curve, List[geo.Curve]) -> bool
    """
       Rhino의 intersection을 사용하기 때문에
       겹쳐진 커브의 intersection event는 제대로 구해지지 않는다
    Args:
        crv (geo.Curve): 교차 기준 선
        crvs (List[geo.Curve]): 교차할 커브들

    Returns:
        bool: 교차여부
    """
    intersection = ghcomp.MultipleCurves([crv] + crvs)
    return bool(intersection.points)


def offset_regions_inward(regions, dist, miter=BIGNUM):
    # type: (geo.Curve | List[geo.Curve], float, int) -> List[geo.Curve]
    """영역 커브를 안쪽으로 offset 한다.
    단일커브나 커브리스트 관계없이 커브 리스트로 리턴한다.

    Args:
        region: offset할 대상 커브
        dist: offset할 거리

    Returns:
        offset 후 커브
    """

    if not dist:
        return regions
    return Comp().polyline_offset(regions, dist, miter).holes


def offset_region_outward(region, dist, miter=BIGNUM):
    # type: (geo.Curve, float, float) -> geo.Curve
    """영역 커브를 바깥쪽으로 offset 한다.
    단일 커브를 받아서 단일 커브로 리턴한다.

    Args:
        region: offset할 대상 커브
        dist: offset할 거리

    Returns:
        offset 후 커브
    """

    if not dist:
        return region
    if not isinstance(region, geo.Curve):
        raise ValueError("region must be curve")
    return Comp().polyline_offset(region, dist, miter).contour[0]


def convert_io_to_list(func):
    """인풋과 아웃풋을 리스트로 만들어주는 데코레이터"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        new_args = []
        for arg in args:
            if isinstance(arg, geo.Curve):
                arg = [arg]
            new_args.append(arg)

        result = func(*new_args, **kwargs)
        if isinstance(result, geo.Curve):
            result = [result]
        if hasattr(result, "__dict__"):
            for key, values in result.__dict__.items():
                if isinstance(values, geo.Curve):
                    setattr(result, key, [values])
        return result

    return wrapper


class Comp:
    class _PolylineOffsetResult:
        def __init__(self):
            self.contour = None  # type: Optional[List[geo.Curve]]
            self.holes = None  # type: Optional[List[geo.Curve]]

    @convert_io_to_list
    def polyline_offset(
        self,
        crvs,
        dists,
        miter=BIGNUM,
        closed_fillet=2,
        open_fillet=2,
        tol=Rhino.RhinoMath.ZeroTolerance,
    ):
        # type: (List[geo.Curve], List[float], int, int, int, float) -> _PolylineOffsetResult
        """TODO
        # ! open_fillet 0 (round)는 ZeroTolerance에 의해서 연산에 부하가 크다.
        따라서 open_fillet을 다른 종류로 사용하거나, tol 값을 조정해서 사용해야한다.
        Args:
            crv (_type_): _description_
            dists (_type_): _description_
            miter : TODO
            closed_fillet : 0 = round, 1 = square, 2 = miter
            open_fillet : 0 = round, 1 = square, 2 = butt

        Returns:
            _type_: _description_
        """
        if tol == Rhino.RhinoMath.ZeroTolerance and open_fillet == 0:
            raise ValueError("open_fillet must be 1 or 2")

        if not crvs:
            raise ValueError("crvs must be more than 1")

        plane = geo.Plane(geo.Point3d(0, 0, crvs[0].PointAtEnd.Z), geo.Vector3d.ZAxis)
        result = ghcomp.ClipperComponents.PolylineOffset(
            crvs,
            dists,
            plane,
            tol,
            closed_fillet,
            open_fillet,
            miter,
        )
        polyline_offset_result = Comp._PolylineOffsetResult()
        for name in ("contour", "holes"):
            setattr(polyline_offset_result, name, result[name])
        return polyline_offset_result
