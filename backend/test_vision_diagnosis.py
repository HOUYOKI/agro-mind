from backend.vision.diagnosis_tool import diagnose_crop_image
import json

image_path = r"D:\agro-mind\backend\data\Agromind_Image\PlantVillage - Sample images\0\0f1197f8-a106-4ebc-ad08-42967be969a8.JPG"

result = diagnose_crop_image(image_path)

print(json.dumps(result, indent=2, ensure_ascii=False))