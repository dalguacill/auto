#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuración
USERNAME = os.environ.get('CLUB_USERNAME', '44711')
PASSWORD = os.environ.get('CLUB_PASSWORD', 'damolto8')
BASE_URL = 'https://cnmolins.miclubonline.net'

def get_target_day():
    """Determina qué día queremos reservar basándonos en el día actual"""
    today = datetime.now()
    day_name = today.weekday()  # 0=Monday, 1=Tuesday, etc.
    
    # Si hoy es lunes (0), reservamos para mañana martes (1)
    # Si hoy es miércoles (2), reservamos para mañana jueves (3)
    # Si hoy es jueves (3), reservamos para mañana viernes (4)
    
    target_days = {
        0: ('martes', 1),      # Lunes -> Reservar Martes
        2: ('jueves', 3),      # Miércoles -> Reservar Jueves
        3: ('viernes', 4),     # Jueves -> Reservar Viernes
    }
    
    if day_name not in target_days:
        print(f"❌ Hoy es {['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][day_name]}, no hay que reservar nada.")
        return None, None
    
    return target_days[day_name]

def book_class():
    """Función principal para reservar la clase"""
    
    target_day_name, target_day_num = get_target_day()
    
    if target_day_name is None:
        return True  # No es un día de reserva
    
    print(f"🎯 Objetivo: Reservar clase de CrossFit para {target_day_name}")
    
    with sync_playwright() as p:
        try:
            # Iniciar navegador
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # 1. Ir a la página de login
            print("📍 Navegando a la página de login...")
            page.goto(f'{BASE_URL}/user/login', wait_until='networkidle')
            
            # 2. Iniciar sesión
            print("🔐 Iniciando sesión...")
            page.fill('#edit-name', USERNAME)
            page.fill('#edit-pass', PASSWORD)
            page.click('#edit-submit')
            page.wait_for_load_state('networkidle')
            
            # Verificar que el login fue exitoso
            if 'login' in page.url:
                print("❌ Error: No se pudo iniciar sesión")
                page.screenshot(path='error_screenshot.png')
                return False
            
            print("✅ Sesión iniciada correctamente")
            
            # 3. Ir a la página de actividades dirigidas
            print("📍 Navegando a actividades dirigidas...")
            page.goto(f'{BASE_URL}/dirigidas', wait_until='networkidle')
            page.wait_for_timeout(3000)  # Esperar a que cargue el calendario
            
            # 4. Buscar la clase de CrossFit del día objetivo a las 19:30
            print(f"🔍 Buscando clase de CrossFit para {target_day_name} 19:30...")
            
            # Intentar encontrar la clase con diferentes textos posibles
            class_selectors = [
                f'text=/19:30.*CROSS TRAIN/i',
                'text=/19:30.*20:15.*CROSS TRAIN/i'
            ]
            
            class_found = False
            for selector in class_selectors:
                try:
                    elements = page.locator(selector).all()
                    print(f"   Encontrados {len(elements)} elementos con selector: {selector}")
                    
                    for element in elements:
                        # Verificar si el elemento es clickeable y está visible
                        if element.is_visible():
                            print("   Elemento visible encontrado, haciendo clic...")
                            element.click(timeout=5000)
                            class_found = True
                            break
                    
                    if class_found:
                        break
                        
                except Exception as e:
                    print(f"   No se encontró con selector {selector}: {e}")
                    continue
            
            if not class_found:
                print("⚠️ No se encontró la clase. Posibles razones:")
                print("   - La clase no está disponible aún (faltan más de 24h)")
                print("   - La clase ya está completa")
                print("   - La clase fue cancelada")
                page.screenshot(path='error_screenshot.png')
                return False
            
            # 5. Esperar a que aparezca el modal
            print("⏳ Esperando modal de reserva...")
            page.wait_for_timeout(2000)
            
            # 6. Verificar si hay botón de Reserva
            try:
                reserve_button = page.locator('button:has-text("Reserva"), input[value="Reserva"]')
                
                if reserve_button.count() == 0:
                    print("⚠️ No hay botón de Reserva disponible.")
                    print("   La clase probablemente no está en la ventana de 24h o está completa.")
                    page.screenshot(path='error_screenshot.png')
                    return False
                
                # 7. Hacer clic en Reserva
                print("🎉 ¡Botón de Reserva encontrado! Reservando...")
                reserve_button.first.click()
                page.wait_for_timeout(3000)
                
                # 8. Verificar confirmación
                print("✅ ¡Reserva completada exitosamente!")
                page.screenshot(path='success_screenshot.png')
                return True
                
            except Exception as e:
                print(f"❌ Error al intentar reservar: {e}")
                page.screenshot(path='error_screenshot.png')
                return False
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            try:
                page.screenshot(path='error_screenshot.png')
            except:
                pass
            return False
        
        finally:
            browser.close()

if __name__ == '__main__':
    success = book_class()
    sys.exit(0 if success else 1)
