from datetime import datetime, timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .firebase import get_firestore_client

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def map_points(request):
    """
    GET  -> lista puntos del usuario autenticado
    POST -> crea un punto (title, lat, lng)
    """
    db = get_firestore_client()
    col = db.collection("map_points")

    if request.method == "GET":
        docs = (
            col.where("user_id", "==", request.user.id)
               .order_by("created_at", direction="DESCENDING")
               .stream()
        )
        results = [{"id": d.id, **d.to_dict()} for d in docs]
        return Response({"results": results}, status=status.HTTP_200_OK)

    title = (request.data.get("title") or "").strip() or "Ubicación guardada"
    try:
        lat = float(request.data["lat"])
        lng = float(request.data["lng"])
    except Exception:
     return Response(
          {"detail": "Se espera lat y lng numéricos."},
         status=status.HTTP_400_BAD_REQUEST
    )



    doc_ref = col.document()
    doc_ref.set({
        "user_id": request.user.id,
        "title": title,
        "lat": lat,
        "lng": lng,
        "created_at": _now_iso(),
    })

    return Response({"id": doc_ref.id}, status=status.HTTP_201_CREATED)