# Contexto del Proyecto y Registro de Cambios

## 1. Problemas Resueltos

### A. Error 404 en la llamada POST al Chat
- **Error reportado:** `[15/Oct/2026 11:45:57] "POST /support/chat/%7Border_id%7D/ HTTP/1.1" 404 2709`
- **Causa raíz:**
  1. En `templates/order_detail.html`, la llamada `fetch` tenía la URL hardcodeada como literal de JavaScript: `'/support/chat/{order_id}/'`. El navegador enviaba `{order_id}` codificado como `%7Border_id%7D`.
  2. En `support/urls.py`, la ruta estaba definida como `'chat/<int:order_id>'` sin barra final (`/`).
- **Solución:** Se corrigió a `{% url 'chat' order.id %}` en el template y se dio soporte de barra final y sin barra en `support/urls.py`.

### B. Fallos en `support/agents.py` al llamar al LLM
- **Causas raíz:**
  1. `NameError: name 'SUPPORT_SYSTEM_PROMPT' is not defined`: En la línea 12 estaba nombrado como `SUPPORT_SYSTEN_PROMPT` (con 'N').
  2. `TypeError: create() missing 1 required positional argument: 'tools'`: El método `create()` en `gemini_client.py` requería obligatoriamente el argumento `tools`. Además, `SUPPORT_TOOLS` estaba definido pero no se pasaba a la llamada.
  3. Mapeo de roles: Los mensajes de agente en base de datos tienen rol `"agent"`, mientras que la API de Anthropic/Gemini espera rol `"assistant"`.
  4. Retorno de valor: `run_support_agent` no retornaba la respuesta de texto para la vista consumidora.
  5. Error en `support/tools.py`: `from time import timezone` causaba `AttributeError: 'int' object has no attribute 'now'`. Se corrigió a `from django.utils import timezone`.
- **Solución:**
  1. Se corrigió el nombre a `SUPPORT_SYSTEM_PROMPT` (manteniendo alias de retrocompatibilidad).
  2. Se pasó `tools=SUPPORT_TOOLS` en la llamada a `client.messages.create()`.
  3. Se hizo `tools=None` opcional por defecto en `gemini_client.py`.
  4. Se normalizó el rol en los mensajes a `"assistant"`.
  5. Se extrajo y retornó el texto (`reply_text`) de los bloques de respuesta.

### C. Burbuja de "Typing..." pegada y "Sorry, something went wrong" (Race Condition en Frontend)
- **Error reportado:** En el widget de chat, al enviar mensajes aparecía "Sorry, something went wrong" y la burbuja "Typing..." se quedaba congelada abajo permanentemente.
- **Causa raíz:**
  1. `setTimeout(() => showTyping(), 2000)` programaba la aparición del indicador para 2 segundos después.
  2. Si la respuesta del servidor llegaba antes de los 2 segundos, `hideTyping()` ejecutaba `document.getElementById('typing-indicator').remove()`. Al no existir todavía el elemento, arrojaba `TypeError: Cannot read properties of null (reading 'remove')`.
  3. Esto disparaba el bloque `catch`, mostrando "Sorry, something went wrong".
  4. Cumplidos los 2 segundos, el temporizador pendiente se ejecutaba e insertaba "Typing..." después del mensaje, quedando atascado en pantalla porque nada lo eliminaba.
- **Solución:**
  1. En `hideTyping()` se valida la existencia del elemento antes de llamar a `.remove()` y se cancela cualquier temporizador activo con `clearTimeout`.
  2. Se muestra el indicador inmediatamente al enviar y se garantiza su remoción dentro de un bloque `finally`.
  3. Se desactiva temporalmente el input durante el envío para evitar envíos múltiples concurrentes.

### D. Error `AttributeError: 'ToolUseBlock' object has no attribute 'text'` en `run_support_agent`
- **Error reportado:** Al enviar un mensaje ("Hi"), la consola mostraba la llamada y ejecución exitosa de la herramienta `get_order_details`, pero inmediatamente después arrojaba:
  `AttributeError: 'ToolUseBlock' object has no attribute 'text'` en `return response.content[0].text`. En la interfaz aparecía "Sorry, something went wrong".
- **Causas raíz:**
  1. **Indentación errónea del `else`:** El bloque `else:` estaba indentado al nivel del `for block in response.content:`, no del `if response.stop_reason == 'tool_use':`. En Python, un `for ... else:` ejecuta el bloque `else` cuando el bucle termina normalmente.
  2. **Acceso a atributo inexistente:** En `response.stop_reason == 'tool_use'`, `response.content[0]` es una instancia de `ToolUseBlock` (no `TextBlock`), por lo que no posee el atributo `.text`.
  3. **Corte prematuro del bucle de herramientas:** Los `conversation_messages.append` se encontraban dentro del bucle de bloques y, al ejecutarse el `else` del `for`, la función retornaba de inmediato en lugar de continuar el ciclo `while True` para que el modelo procesara los resultados de la herramienta y generara la respuesta final al usuario.
- **Solución:**
  1. Se ajustó la indentación de los `append` a `conversation_messages` fuera del `for block in response.content:`.
  2. Se asoció el `else:` correctamente al `if response.stop_reason == 'tool_use':`.
  3. En la rama `else:`, se itera sobre los bloques de respuesta para extraer el texto de los objetos de tipo `text` de forma segura (`block.text`).
  4. Cuando `response.stop_reason == 'tool_use'`, la función no retorna; en su lugar, agrega el mensaje del asistente y el resultado de la herramienta al historial y continúa el ciclo `while True`, permitiendo a Maya generar la respuesta final natural para el cliente.

### E. Error 404 "No Conversation matches the given query" en `order_detail`
- **Error reportado:** Al hacer clic en "View" para una orden (ej. orden 4, `http://127.0.0.1:8000/orders/4/`), Django arrojaba:
  `Page not found (404) - No Conversation matches the given query.` en `orders.views.order_detail`.
- **Causa raíz:**
  1. En `orders/views.py`, la vista `order_detail` utilizaba `get_object_or_404(Conversation, user=request.user, order=order)`.
  2. Para órdenes nuevas o en las que el usuario aún no había iniciado una conversación de soporte, no existía ningún registro de `Conversation` en la base de datos.
  3. `get_object_or_404` lanzaba un `Http404` impidiendo ver los detalles de la orden.
  4. Adicionalmente, `order_detail` no tenía el decorador `@login_required` a diferencia de `orders_list`.
- **Solución:**
  1. Se reemplazó `get_object_or_404(Conversation, ...)` por `Conversation.objects.get_or_create(user=request.user, order=order)`, garantizando que si no existe una conversación previa, se cree automáticamente una instancia vacía sin bloquear el acceso al detalle de la orden.
  2. Se añadió el decorador `@login_required` a la función `order_detail`.

---

## 2. Archivos Modificados

### 1) `templates/order_detail.html`
- Corrección de la lógica de `showTyping()`, `hideTyping()` y `sendMessage()`.
- Protección contra `null` al eliminar `typing-indicator`.
- Desactivación de input durante el envío y limpieza garantizada en bloque `finally`.

### 2) `support/agents.py`
- Corrección de `SUPPORT_SYSTEM_PROMPT`.
- Paso de `tools=SUPPORT_TOOLS` en `client.messages.create(...)`.
- Mapeo de roles `"agent"` a `"assistant"`.
- Corrección completa del bucle agéntico con llamadas a herramientas (`tool_use`) y respuesta final (`end_turn`).
- Extracción segura del texto de respuesta.

### 3) `support/gemini_client.py`
- Parámetro `tools=None` por defecto en `create()`.
- Soporte para mensajes con rol `"agent"` mapeados a `"model"`.
- Validación segura si `tools` es nulo o vacío en `_convert_tools`.

### 4) `support/tools.py`
- Corrección de `from django.utils import timezone` en lugar de `from time import timezone`.
- Manejo seguro de `Order.DoesNotExist` dentro del bloque `try`.

### 5) `support/views.py`
- Importación de `run_support_agent`.
- Corrección en `Conversation.objects.get_or_create(order=order, user=request.user)`.
- Guardado y retorno de la respuesta real del agente.

### 6) `support/urls.py`
- Soporte con y sin barra final para `chat/<int:order_id>/`.

### 7) `dj_ai_employee_main/settings.py`
- Configuración de logging de errores en `logs/django_errors.log`.

### 8) `orders/views.py`
- Se agregó `@login_required` a `order_detail`.
- Se cambió `get_object_or_404(Conversation, ...)` por `Conversation.objects.get_or_create(user=request.user, order=order)`.

### 9) `public_html/ext/test_agent_flow.py`
- Script de prueba creado en zona de pruebas (`public_html/ext/`) para validar el ciclo completo del agente.

---

## 3. Rutas Afectadas
- `GET /orders/<int:order_id>/` (nombre de ruta: `order_detail`)
- `POST /support/chat/<order_id>/` (nombre de ruta: `chat`)

---

## 4. Consultas SQL
- *Ninguna query directa requerida. Se usan modelos ORM de Django.*

---

## 5. Instrucciones de Prueba Manual
1. Iniciar o mantener el servidor Django:
   ```powershell
   .\env\Scripts\python.exe manage.py runserver
   ```
2. En el navegador:
   - Ir a la lista de órdenes `http://127.0.0.1:8000/orders/`.
   - Hacer clic en el botón **"View"** de la orden 4 (`http://127.0.0.1:8000/orders/4/`).
   - Verificar que la página carga correctamente con los detalles del pedido y la interfaz de soporte de Maya lista para conversar (sin error 404).

---

## 6. Tareas Pendientes
- Integrar la llamada a las demás herramientas (`get_refund_history` y `check_delivery_status`) según el flujo conversacional del usuario.
- Registrar los eventos de pasos y herramientas en `AgentLog` dentro de la base de datos para trazabilidad.

