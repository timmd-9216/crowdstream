#!/usr/bin/env python3
"""Script para verificar la disponibilidad de bibliotecas de time-stretching.

Este script verifica qué métodos de time-stretching están disponibles:
- playback_rate: Siempre disponible (método básico)
- pyrubberband: Requiere pyrubberband + librería C Rubber Band
- audiotsm: Requiere audiotsm (solo Python, sin dependencias C)

Uso:
    # Desde el directorio raíz del proyecto
    python3 audio-mixer/check_time_stretch_libs.py
    
    # O desde audio-mixer/ (con venv activado)
    cd audio-mixer
    source venv/bin/activate  # si usas venv
    python check_time_stretch_libs.py
"""

import sys
import os
import platform
from pathlib import Path


def check_pyrubberband():
    """Verifica si pyrubberband está disponible."""
    print("🔍 Verificando pyrubberband...")
    try:
        import pyrubberband as pyrb
        print("  ✅ pyrubberband importado correctamente")
        
        # Intentar una operación básica
        import numpy as np
        test_audio = np.zeros((1000, 2), dtype=np.float32)
        try:
            result = pyrb.time_stretch(test_audio, 44100, 1.0)
            print("  ✅ pyrubberband.time_stretch() funciona correctamente")
            return True, None
        except Exception as e:
            print(f"  ⚠️  pyrubberband importado pero time_stretch() falló: {e}")
            return False, str(e)
    except ImportError as e:
        print(f"  ❌ pyrubberband no está disponible: {e}")
        print("     Instalación:")
        print("      1. Instalar librería C: brew install rubberband (macOS) o apt-get install librubberband-dev (Linux)")
        print("      2. Instalar Python: pip install pyrubberband")
        return False, str(e)
    except Exception as e:
        print(f"  ❌ Error inesperado con pyrubberband: {e}")
        return False, str(e)


def check_audiotsm():
    """Verifica si audiotsm está disponible."""
    print("\n🔍 Verificando audiotsm...")
    try:
        import audiotsm
        from audiotsm import wsola
        from audiotsm.io.array import ArrayReader, ArrayWriter
        print("  ✅ audiotsm importado correctamente")
        
        # Intentar una operación básica
        import numpy as np
        test_audio = np.zeros((1000, 2), dtype=np.float32)
        channels_first = test_audio.T
        reader = ArrayReader(channels_first)
        writer = ArrayWriter(channels=2)
        tsm = wsola(reader.channels, speed=1.0)
        print("  ✅ audiotsm.wsola funciona correctamente")
        return True, None
    except ImportError as e:
        print(f"  ❌ audiotsm no está disponible: {e}")
        print("     Instalación: pip install audiotsm")
        return False, str(e)
    except Exception as e:
        print(f"  ❌ Error inesperado con audiotsm: {e}")
        return False, str(e)


def main():
    """Función principal que verifica todas las bibliotecas."""
    print("=" * 60)
    print("Verificación de bibliotecas de time-stretching")
    print("=" * 60)
    
    # Mostrar información del entorno
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    print(f"\n📁 Directorio del proyecto: {project_root}")
    
    python_executable = sys.executable
    
    # Detectar si estamos en un venv
    venv_detected = False
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_detected = True
        venv_path = sys.prefix
        print(f"📦 Entorno virtual: {venv_path}")
        print(f"   ✅ Usando entorno virtual")
    else:
        print(f"📦 Entorno: Python del sistema")
        print(f"   💡 Tip: Activa un venv para aislar dependencias")
    
    print(f"\n💻 Sistema: {platform.system()} {platform.machine()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📍 Ejecutable: {python_executable}\n")
    
    results = {}
    
    # Verificar playback_rate (siempre disponible)
    print("🔍 Verificando playback_rate...")
    print("  ✅ playback_rate siempre disponible (método básico)")
    results['playback_rate'] = True
    
    # Verificar otras bibliotecas
    results['pyrubberband'], _ = check_pyrubberband()
    results['audiotsm'], _ = check_audiotsm()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for method, available in results.items():
        status = "✅ DISPONIBLE" if available else "❌ NO DISPONIBLE"
        print(f"{status:20} {method}")
    
    available_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nMétodos disponibles: {available_count}/{total_count}")
    
    if available_count == 1:
        print("\n⚠️  Solo playback_rate está disponible.")
        print("   Para mejor calidad, instala al menos una de:")
        print("   - pyrubberband (alta calidad)")
        print("   - audiotsm (rápido)")
    elif available_count > 1:
        print(f"\n✅ {available_count} métodos disponibles para time-stretching")
    
    # Recomendaciones
    print("\n" + "=" * 60)
    print("RECOMENDACIONES")
    print("=" * 60)
    
    if results['pyrubberband']:
        print("✅ pyrubberband: Mejor calidad, recomendado para producción")
    elif results['audiotsm']:
        print("✅ audiotsm: Rápido, bueno para tiempo real")
    else:
        print("⚠️  Solo playback_rate disponible (cambia el pitch)")
        print("   Recomendado instalar al menos audiotsm para mejor calidad")
    
    return 0 if available_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

