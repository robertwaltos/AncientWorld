## API Key Setup Guide

### Rijksmuseum API Key (Free, Instant)
1. Visit: https://data.rijksmuseum.nl/object-metadata/api/
2. Click "Request API key" or "Get API key"
3. Fill in the simple form (name, email, purpose: "academic research")
4. You'll receive the key immediately via email
5. Add to `.env` file: `RIJKSMUSEUM_API_KEY=your-key-here`

**Collection Size**: 700,000+ artworks including Dutch architecture, paintings, drawings

### Smithsonian API Key (Free, Instant)
1. Visit: https://api.si.edu/signup
2. Sign up with email
3. Receive key immediately
4. Add to `.env` file: `SMITHSONIAN_API_KEY=your-key-here`

**Collection Size**: 11+ million items including architectural drawings, photographs

### British Library (No API Key Required)
Uses IIIF Image API - no authentication needed
**Collection Size**: 1+ million digitized images

### Getty Museum (No API Key Required)
Uses open API - no authentication needed
**Collection Size**: 100,000+ artworks

---

Once you have the API keys, add them to: `d:\PythonProjects\AncientWorld\.env`
