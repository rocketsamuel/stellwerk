from config import ROUTES


def find_route(
    start,
    target
):

    for name, route in ROUTES.items():

        if (
            route["start"] == start
            and
            route["target"] == target
        ):

            return name, route

    return None, None
