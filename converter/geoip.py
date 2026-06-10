def get_user_country(request):
    """
    Detects the country of the request using Cloudflare's HTTP_CF_IPCOUNTRY header.
    Allows query parameter `?geoip_mock=XX` (e.g. `?geoip_mock=US`) for developer testing.
    """
    # 1. Check for developer mock query parameter (e.g. ?geoip_mock=US)
    geoip_mock = request.GET.get('geoip_mock')
    if geoip_mock:
        return geoip_mock.upper()

    # 2. Check Cloudflare header (Edge Geolocation)
    country = request.META.get('HTTP_CF_IPCOUNTRY')
    if country:
        return country.upper()

    # Default fallback to India (IN)
    return 'IN'
