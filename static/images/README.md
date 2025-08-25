# Adventure Images

This directory contains cover images for adventures.

## Directory Structure
```
static/
└── images/
    └── adventures/
        ├── crypt_serpent_king.jpg
        ├── sky_fortress_escape.jpg
        └── starship_voyager_mystery.jpg
```

## Image Requirements
- **Format**: JPG, PNG, WebP
- **Size**: Recommended 800x600px or 16:9 aspect ratio
- **File Size**: Keep under 500KB for optimal loading

## Adding New Images
1. Place image files in `static/images/adventures/`
2. Update the corresponding adventure in `adventures.json`
3. Set the `image` field to the filename (e.g., "my_adventure.jpg")

## API Access
Images are served via FastAPI static files at:
- URL pattern: `http://localhost:8000/static/images/adventures/{filename}`
- The API automatically generates `image_url` fields in adventure responses

## Frontend Usage
When fetching adventures from `/adventures/`, each adventure will include:
```json
{
  "id": 1,
  "title": "Adventure Title",
  "image": "filename.jpg"
}
```