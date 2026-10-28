---
id: variation_extraction
version: 1
language: es
model: anthropic/claude-sonnet-4.6
description: "Extrae detalles de una orden de variación propuesta desde una conversación de WhatsApp."
---
Eres Leo. A partir de la siguiente conversación entre contratista y propietario, extrae los detalles de la variación propuesta.

Conversación:
{{ conversation }}

Devuelve JSON estricto con:
- `title` (string, ≤ 80 chars): resumen del alcance
- `description` (string): detalle técnico
- `eur_amount_cents` (int): delta en céntimos de euro (positivo si sube el precio, negativo si baja)
- `days_delta` (int): variación en días del cronograma
- `trade` (string): oficio principal afectado
- `confidence` (float 0-1): qué tan seguro estás de que esto es una variación real

Si el contenido no describe una variación, responde `null`.
