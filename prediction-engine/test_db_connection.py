"""
test_db_connection.py
Script de test de connexion PostgreSQL pour le moteur de prédiction Python
Usage: python test_db_connection.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def test_connection():
    print("\n🔌 Test de connexion PostgreSQL (DevMind Prediction Engine)\n")
    print(f"DATABASE_URL: {'✅ Définie' if DATABASE_URL else '❌ Non définie'}")

    if not DATABASE_URL:
        print("\n❌ DATABASE_URL non définie. Créez votre fichier .env à partir de .env.example\n")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("\n❌ psycopg2 non installé. Exécutez : pip install -r requirements.txt\n")
        sys.exit(1)

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()

        print("\n✅ Connexion réussie à PostgreSQL !\n")

        # Test 1 : Version PostgreSQL
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"📦 Version PostgreSQL: {' '.join(version.split()[:2])}")

        # Test 2 : Lister les tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        if not tables:
            print("\n⚠️  Aucune table trouvée — exécutez la migration Node.js d'abord :")
            print("   cd ../backend && npm run migrate\n")
        else:
            print(f"\n📋 Tables trouvées ({len(tables)}) :")
            for t in tables:
                print(f"   - {t}")

            # Test 3 : Tables critiques pour le moteur Python
            expected = [
                'matches', 'predictions', 'markets', 'ai_models',
                'leagues', 'teams', 'coupons', 'coupon_predictions',
                'prediction_results', 'risk_factors'
            ]
            missing = [t for t in expected if t not in tables]
            if missing:
                print(f"\n⚠️  Tables manquantes : {', '.join(missing)}")
            else:
                print("\n✅ Toutes les tables requises pour le moteur Python sont présentes !")

            # Test 4 : Modèles IA disponibles
            cur.execute("SELECT name, version FROM ai_models WHERE is_active = TRUE")
            models = cur.fetchall()
            if models:
                print(f"\n🤖 Modèles IA actifs ({len(models)}) :")
                for name, version in models:
                    print(f"   - {name} v{version}")

            # Test 5 : Marchés disponibles
            cur.execute("SELECT code, name FROM markets WHERE is_active = TRUE")
            markets = cur.fetchall()
            if markets:
                print(f"\n🎯 Marchés actifs ({len(markets)}) :")
                for code, name in markets:
                    print(f"   - {code}: {name}")

        cur.close()
        conn.close()
        print("\n✅ Tous les tests ont réussi !\n")

    except psycopg2.OperationalError as e:
        print(f"\n❌ Erreur de connexion: {e}")
        print("\nVérifiez :")
        print("  1. Que DATABASE_URL est correctement définie dans .env")
        print("  2. Que votre base de données Neon.tech / Supabase est accessible")
        print("  3. Que les options SSL sont correctes\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
