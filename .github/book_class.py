#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# =========================
# CONFIGURACIÓN BÁSICA
# =========================

USERNAME = os.environ.get('CLUB_USERNAME', '44711')
PASSWORD = os.environ.get('CLUB_PASSWORD', 'damolto8')
BASE_URL = 'https://cnmolins.miclubonline.net'

# Crear carpetas si no existen
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

# Configuración del logger
logging.basicConfig(
    filename="logs/book_class.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log(msg):
    """Imprime y guarda mensajes de log."""
    print(msg)
    logging.info(msg)


# =========================
# LÓGICA DE FECHAS
# =========================

def get_target_day():
    """Determina qué día queremos reservar basándonos en el día actual"""
    today = datetime.now()
    day_name = today.weekday()
    
    target_days = {
        0: ('martes', 1),      # Lunes -> Reservar Martes
        2: ('jueves', 3),      # Miércoles -> Reservar Jueves
        3: ('viernes', 4),     # Jueves -> Reservar Viernes
    }
    
    if day_name not in target_days:
        log(f"ℹ️ Hoy es {['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][day_name]}, no hay que reservar nada.")
        return None, None
    
    return target_days[day_name]


# =========================
# FUNCIÓN PRINCIPAL
# =========================

def book_class():
    """Función principal para reservar la clase"""
    
    target_day_name, target_day_num = get_target_day()
    if target_day_name is None:
        return True  # No hay nada que reservar hoy

    log(f"🎯 Objetivo: Reservar clase de CrossFit para {target_day_name}")
    log(f"⏰ Fecha/Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    browser = None
    page = None

    try:
        with sync_playwright() as p:
            log("🚀 Iniciando Playwright...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            # 1. Ir a login
            log("📍 Navegando a la página de login...")
            page.goto(f'{BASE_URL}/user/login', wait_until='networkidle', timeout=30000)
            page.screenshot(path='screenshots/step1_login_page.png')

            # 2. Iniciar sesión
            log("🔐 Iniciando sesión...")
            page.fill('#edit-name', USERNAME)
            page.fill('#edit-pass', PASSWORD)
            page.screenshot(path='screenshots/step2_before_submit.png')
            
            page.click('#edit-submit')
            page.wait_for_load_state('networkidle', timeout=30000)
            page.screenshot(path='screenshots/step3_after_login.png')
            
            if 'login' in page.url:
                log("❌ Error: No se pudo iniciar sesión")
                page.screenshot(path='screenshots/error_login.png')
                return False
            
            log("✅ Sesión iniciada correctamente")

            # 3. Ir a actividades dirigidas
            log("📍 Navegando a actividades dirigidas...")
            page.goto(f'{BASE_URL}/dirigidas', wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path='screenshots/step4_calendar.png')

            # 4. Buscar clase
            log(f"🔍 Buscando clase de CrossFit para {target_day_name} 19:30...")
            class_found = False

            # Estrategia 1
            try:
                log("   Estrategia 1: Buscando por texto en enlaces...")
                links = page.locator('a').all()
                log(f"   Encontrados {len(links)} enlaces.")
                for link in links:
                    try:
                        text = link.inner_text(timeout=1000)
                        if '19:30' in text and 'CROSS TRAIN' in text.upper():
                            log(f"   ✓ Encontrado: {text[:80]}")
                            if link.is_visible():
                                link.click(timeout=5000)
                                class_found = True
                                break
                    except Exception:
                        continue
            except Exception as e:
                log(f"   Estrategia 1 falló: {e}")

            # Estrategia 2
            if not class_found:
                try:
                    log("   Estrategia 2: Buscando bloque horario...")
                    elements = page.get_by_text('19:30').all()
                    log(f"   Encontrados {len(elements)} elementos con 19:30")
                    for elem in elements:
                        parent = elem.locator('xpath=ancestor::a').first
                        if parent.count() > 0:
                            text = parent.inner_text()
                            if 'CROSS TRAIN' in text.upper():
                                log(f"   ✓ Encontrado en bloque padre: {text[:80]}")
                                parent.click(timeout=5000)
                                class_found = True
                                break
                except Exception as e:
                    log(f"   Estrategia 2 falló: {e}")

            if not class_found:
                log("⚠️ No se encontró la clase. Puede que aún no esté disponible o esté completa.")
                page.screenshot(path='screenshots/error_class_not_found.png')
                return False

            # 5. Esperar modal
            log("⏳ Esperando modal de reserva...")
            page.wait_for_timeout(2000)
            page.screenshot(path='screenshots/step5_modal.png')

            # 6. Buscar botón de Reserva
            log("🔍 Buscando botón de Reserva...")
            reserve_selectors = [
                'button:has-text("Reserva")',
                'input[value="Reserva"]',
                'button:text("Reserva")',
                'a:has-text("Reserva")'
            ]
            
            reserve_button = None
            for selector in reserve_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0:
                        reserve_button = btn
                        log(f"   ✓ Botón encontrado con selector: {selector}")
                        break
                except Exception:
                    continue

            if reserve_button is None or reserve_button.count() == 0:
                log("⚠️ No hay botón de Reserva disponible.")
                page.screenshot(path='screenshots/error_no_button.png')
                return False

            # 7. Reservar
            log("🎉 ¡Botón de Reserva encontrado! Reservando...")
            page.screenshot(path='screenshots/step6_before_reserve.png')
            reserve_button.first.click(timeout=5000)
            page.wait_for_timeout(3000)
            page.screenshot(path='screenshots/step7_after_reserve.png')

            log("✅ ¡Reserva completada exitosamente!")
            return True

    except Exception as e:
        log(f"❌ Error general: {e}")
        import traceback
        logging.error(traceback.format_exc())
        if page:
            try:
                page.screenshot(path='screenshots/error_general.png')
            except Exception:
                pass
        return False

    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass


# =========================
# PUNTO DE ENTRADA
# =========================

if __name__ == '__main__':
    try:
        success = book_class()
        sys.exit(0 if success else 1)
    except Exception as e:
        log(f"❌ Error fatal: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)
