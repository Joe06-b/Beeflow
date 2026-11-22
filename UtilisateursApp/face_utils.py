
import base64
import json

import cv2
import numpy as np
from deepface import DeepFace


# Modèle utilisé pour toutes les captures
MODEL_NAME = "ArcFace"

# Seuil initial de similarité cosinus
# À ajuster après les tests avec de vraies captures
FACE_THRESHOLD = 0.68


def decode_base64_image(image_base64):
    """Convertit une image Base64 en image OpenCV."""
    try:
        if not image_base64:
            return None

        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        image_array = np.frombuffer(image_bytes, np.uint8)

        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    except Exception:
        return None


def extract_face_data(image_bgr):
    """
    Utilise DeepFace et ArcFace pour détecter le visage
    et extraire son vecteur de caractéristiques.
    """
    if image_bgr is None:
        raise ValueError("Image invalide.")

    representations = DeepFace.represent(
        img_path=image_bgr,
        model_name=MODEL_NAME,
        detector_backend="opencv",
        enforce_detection=True
    )

    if len(representations) != 1:
        raise ValueError(
            "Veuillez présenter un seul visage devant la caméra."
        )

    embedding = np.array(
        representations[0]["embedding"],
        dtype="float32"
    )

    facial_area = representations[0].get("facial_area", {})

    return embedding, facial_area


def extract_face_features(image_bgr):
    """Extrait le vecteur facial avec ArcFace."""
    try:
        embedding, _ = extract_face_data(image_bgr)
        return embedding
    except Exception:
        return None


def create_face_thumbnail(image_bgr, facial_area):
    """Crée une miniature du visage capturé."""
    h, w = image_bgr.shape[:2]

    x = max(0, int(facial_area.get("x", 0)))
    y = max(0, int(facial_area.get("y", 0)))
    face_w = int(facial_area.get("w", w))
    face_h = int(facial_area.get("h", h))

    x2 = min(w, x + face_w)
    y2 = min(h, y + face_h)

    face_crop = image_bgr[y:y2, x:x2]

    if face_crop.size == 0:
        face_crop = image_bgr

    thumbnail = cv2.resize(face_crop, (100, 100))

    success, buffer = cv2.imencode(
        ".jpg",
        thumbnail,
        [cv2.IMWRITE_JPEG_QUALITY, 85]
    )

    if not success:
        return None

    encoded = base64.b64encode(buffer).decode("utf-8")

    return "data:image/jpeg;base64," + encoded


def process_and_encode_face(image_base64):
    """
    Capture le visage, extrait son embedding ArcFace
    et prépare les données à enregistrer dans Django.
    """
    image = decode_base64_image(image_base64)

    if image is None:
        return False, "Image invalide ou non reçue.", None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if np.mean(gray) < 20:
        return (
            False,
            "L'image est trop sombre. Améliorez l'éclairage.",
            None
        )

    try:
        embedding, facial_area = extract_face_data(image)

        thumbnail = create_face_thumbnail(image, facial_area)

        payload = {
            "version": "2.0",
            "model": MODEL_NAME,
            "embedding": embedding.tolist(),
            "thumbnail": thumbnail
        }

        return (
            True,
            "Visage capturé et encodé avec succès.",
            json.dumps(payload)
        )

    except Exception:
        return (
            False,
            "Aucun visage unique n'a pu être détecté. "
            "Veuillez bien cadrer votre visage.",
            None
        )


def calculate_similarity(vector1, vector2):
    """Calcule la similarité cosinus entre deux embeddings."""
    try:
        v1 = np.asarray(vector1, dtype="float32")
        v2 = np.asarray(vector2, dtype="float32")

        if v1.shape != v2.shape:
            return 0.0

        if not np.all(np.isfinite(v1)) or not np.all(np.isfinite(v2)):
            return 0.0

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0

        similarity = np.dot(v1, v2) / (norm1 * norm2)

        return float(similarity)

    except Exception:
        return 0.0


def authenticate_face(
    image_base64,
    active_users_queryset,
    threshold=FACE_THRESHOLD
):
    """
    Compare le visage capturé avec les embeddings ArcFace
    des utilisateurs configurés.
    """
    image = decode_base64_image(image_base64)

    if image is None:
        return None, 0.0, "Impossible de lire la capture de la caméra."

    try:
        candidate_embedding, _ = extract_face_data(image)

    except Exception:
        return (
            None,
            0.0,
            "Aucun visage unique n'a été détecté."
        )

    best_user = None
    best_score = -1.0

    for user in active_users_queryset:

        if not user.face_configured or not user.face_encoding:
            continue

        try:
            data = json.loads(user.face_encoding)

            # Refuser les anciens encodages de l'algorithme artisanal
            if data.get("model") != MODEL_NAME:
                continue

            stored_embedding = data.get("embedding")

            if not stored_embedding:
                continue

            similarity = calculate_similarity(
                candidate_embedding,
                stored_embedding
            )

            if similarity > best_score:
                best_score = similarity
                best_user = user

        except (ValueError, TypeError, json.JSONDecodeError):
            continue

    if best_user and best_score >= threshold:
        return (
            best_user,
            best_score,
            "Authentification faciale réussie."
        )

    return (
        None,
        max(0.0, best_score),
        "Visage non reconnu."
    )
