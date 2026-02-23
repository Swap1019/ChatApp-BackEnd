class MediaCorsMiddleware:
    """
    Ensure media files can be embedded from the frontend dev origin.
    Prevents browser ORB/CORP blocking for cross-origin <img> and CSS backgrounds.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/media/"):
            response["Cross-Origin-Resource-Policy"] = "cross-origin"
            response["Access-Control-Allow-Origin"] = "*"
            response["Vary"] = "Origin"

        return response
