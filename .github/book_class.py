#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

USERNAME = os.environ.get('CLUB_USERNAME', '44711')
PASSWORD = os.environ.get('CLUB_PASSWORD', 'damolto8')
BASE_URL = 'https://cnmolins.miclubonline.net'

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
        print(f"ℹ️ Hoy es {['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][day_name]}, no hay que reservar nada.")
        return None, None
    
    return target_days[day_name]

def book_class():
    """Función principal para reservar la clase"""
    
    target_day_name, target_day_num = get_target_day()
    
    if target_day_name is None:
        return True  # No es día de reserva, salir exitosamente
    
    print(f"🎯 Objetivo: Reservar clase de CrossFit para {target_day_name}")
    print(f"⏰ Fecha/Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    browser = None
    try:
        with sync_playwright() as p:
            # Iniciar navegador
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # 1. Ir a la página de login
            print("📍 Navegando a la página de login...")
            page.goto(f'{BASE_URL}/user/login', wait_until='networkidle', timeout=30000)
            page.screenshot(path='step1_login_page.png')
            
            # 2. Iniciar sesión
            print("🔐 Iniciando sesión...")
            page.fill('#edit-name', USERNAME)
            page.fill('#edit-pass', PASSWORD)
            page.screenshot(path='step2_before_submit.png')
            
            page.click('#edit-submit')
            page.wait_for_load_state('networkidle', timeout=30000)
            page.screenshot(path='step3_after_login.png')
            
            # Verificar que el login fue exitoso
            if 'login' in page.url:
                print("❌ Error: No se pudo iniciar sesión")
                page.screenshot(path='error_screenshot.png')
                return False
            
            print("✅ Sesión iniciada correctamente")
            
            # 3. Ir a la página de actividades dirigidas
            print("📍 Navegando a actividades dirigidas...")
            page.goto(f'{BASE_URL}/dirigidas', wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path='step4_calendar.png')
            
            # 4. Buscar la clase de CrossFit
            print(f"🔍 Buscando clase de CrossFit para {target_day_name} 19:30...")
            
            # Intentar múltiples estrategias para encontrar la clase
            class_found = False
            
            # Estrategia 1: Buscar por texto que contenga 19:30 y CROSS TRAIN
            try:
                print("   Estrategia 1: Buscando por texto...")
                links = page.locator('a').all()
                print(f"   Encontrados {len(links)} enlaces en la página")
                
                for link in links:
                    try:
                        text = link.inner_text(timeout=1000)
                        if '19:30' in text and 'CROSS TRAIN' in text.upper():
                            print(f"   ✓ Encontrado: {text[:100]}")
                            if link.is_visible():
                                link.click(timeout=5000)
                                class_found = True
                                break
                    except:
                        continue
            except Exception as e:
                print(f"   Estrategia 1 falló: {e}")
            
            # Estrategia 2: Buscar específicamente el bloque horario
            if not class_found:
                try:
                    print("   Estrategia 2: Buscando bloque horario...")
                    # Buscar cualquier elemento que tenga el texto con 19:30
                    elements = page.get_by_text('19:30').all()
                    print(f"   Encontrados {len(elements)} elementos con 19:30")
                    
                    for elem in elements:
                        parent = elem.locator('xpath=ancestor::a').first
                        if parent.count() > 0:
                            text = parent.inner_text()
                            if 'CROSS TRAIN' in text.upper():
                                print(f"   ✓ Encontrado en padre: {text[:100]}")
                                parent.click(timeout=5000)
                                class_found = True
                                break
                except Exception as e:
                    print(f"   Estrategia 2 falló: {e}")
            
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
            page.screenshot(path='step5_modal.png')
            
            # 6. Buscar el botón de Reserva
            print("🔍 Buscando botón de Reserva...")
            
            try:
                # Intentar diferentes selectores para el botón
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
                            print(f"   ✓ Botón encontrado con selector: {selector}")
                            break
                    except:
                        continue
                
                if reserve_button is None or reserve_button.count() == 0:
                    print("⚠️ No hay botón de Reserva disponible.")
                    print("   La clase probablemente no está en la ventana de 24h o está completa.")
                    page.screenshot(path='error_screenshot.png')
                    
                    # Mostrar el HTML del modal para debug
                    modal_html = page.locator('body').inner_html()
                    print(f"   HTML del modal (primeros 500 chars): {modal_html[:500]}")
                    return False
                
                # 7. Hacer clic en Reserva
                print("🎉 ¡Botón de Reserva encontrado! Reservando...")
                page.screenshot(path='step6_before_reserve.png')
                
                reserve_button.first.click(timeout=5000)
                page.wait_for_timeout(3000)
                
                page.screenshot(path='step7_after_reserve.png')
                
                # 8. Verificar confirmación
                print("✅ ¡Reserva completada exitosamente!")
                return True
                
            except Exception as e:
                print(f"❌ Error al intentar reservar: {e}")
                page.screenshot(path='error_screenshot.png')
                return False
                
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            if browser and page:
                page.screenshot(path='error_screenshot.png')
        except:
            pass
        return False
    
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass

if __name__ == '__main__':
    try:
        success = book_class()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
  
