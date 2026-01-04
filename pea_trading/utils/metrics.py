"""
Module pour pousser des métriques vers Prometheus Pushgateway
"""
import time
import os
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, pushadd_to_gateway
from prometheus_client.exposition import basic_auth_handler


class MetricsHandler:
    """Gestionnaire de métriques Prometheus pour les jobs cron"""
    
    def __init__(self, pushgateway_url=None):
        """
        Initialise le gestionnaire de métriques
        
        Args:
            pushgateway_url: URL du Pushgateway (défaut: pushgateway:9091)
        """
        self.pushgateway_url = pushgateway_url or os.getenv('PUSHGATEWAY_URL', 'pushgateway:9091')
        
    def push_job_metrics(self, job_name, success, duration, records=0, error_message=None):
        """
        Pousse les métriques d'un job vers le Pushgateway
        
        Args:
            job_name: Nom du job (ex: 'export_transactions_PEA')
            success: True si succès, False si échec
            duration: Durée d'exécution en secondes
            records: Nombre d'enregistrements traités (optionnel)
            error_message: Message d'erreur si échec (optionnel)
        """
        registry = CollectorRegistry()
        
        # Métrique : Succès du job (1=succès, 0=échec)
        g_success = Gauge(
            'cron_job_success', 
            'Job execution success status (1=success, 0=failure)',
            ['job_name'],
            registry=registry
        )
        g_success.labels(job_name=job_name).set(1 if success else 0)
        
        # Métrique : Durée d'exécution
        g_duration = Gauge(
            'cron_job_duration_seconds',
            'Job execution duration in seconds',
            ['job_name'],
            registry=registry
        )
        g_duration.labels(job_name=job_name).set(duration)
        
        # Métrique : Nombre d'enregistrements traités
        g_records = Gauge(
            'cron_job_records_processed',
            'Number of records processed by the job',
            ['job_name'],
            registry=registry
        )
        g_records.labels(job_name=job_name).set(records)
        
        # Métrique : Timestamp de dernière exécution
        g_timestamp = Gauge(
            'cron_job_last_execution_timestamp',
            'Timestamp of last job execution',
            ['job_name'],
            registry=registry
        )
        g_timestamp.labels(job_name=job_name).set(time.time())
        
        # Métrique : Compteur d'erreurs
        if not success and error_message:
            g_error = Gauge(
                'cron_job_error',
                'Job error information',
                ['job_name', 'error_type'],
                registry=registry
            )
            error_type = type(error_message).__name__ if isinstance(error_message, Exception) else 'unknown'
            g_error.labels(job_name=job_name, error_type=error_type).set(1)
        
        # Pousser les métriques vers le Pushgateway
        # Utilise pushadd_to_gateway pour ajouter sans écraser les métriques des autres jobs
        try:
            pushadd_to_gateway(
                self.pushgateway_url,
                job='cron_jobs',
                registry=registry,
                grouping_key={'job_name': job_name}
            )
            print(f"✅ Métriques poussées pour {job_name} (success={success}, duration={duration:.2f}s, records={records})")
        except Exception as e:
            print(f"❌ Erreur lors du push des métriques pour {job_name}: {e}")
    
    def push_scraping_metrics(self, success, duration, stocks_scraped, 
                              stocks_matched, stocks_updated, history_created,
                              history_updated, match_rate, error_message=""):
        """
        Pousse les métriques du scraping intraday vers le Pushgateway
        
        Args:
            success: True si succès, False si échec
            duration: Durée totale du scraping en secondes
            stocks_scraped: Nombre total d'actions trouvées sur Boursorama
            stocks_matched: Nombre d'actions matchées avec notre BDD (par ISIN)
            stocks_updated: Nombre d'actions effectivement mises à jour
            history_created: Nouveaux enregistrements StockPriceHistory créés
            history_updated: Enregistrements StockPriceHistory mis à jour
            match_rate: Taux de match (matched/scraped en pourcentage)
            error_message: Message d'erreur si échec (optionnel)
        """
        registry = CollectorRegistry()
        
        # Métrique : Succès du scraping (1=succès, 0=échec)
        g_success = Gauge(
            'scraping_success',
            'Scraping execution success status (1=success, 0=failure)',
            registry=registry
        )
        g_success.set(1 if success else 0)
        
        # Métrique : Durée du scraping
        g_duration = Gauge(
            'scraping_duration_seconds',
            'Scraping execution duration in seconds',
            registry=registry
        )
        g_duration.set(duration)
        
        # Métrique : Actions scrapées sur Boursorama
        g_scraped = Gauge(
            'scraping_stocks_scraped_total',
            'Total number of stocks scraped from Boursorama',
            registry=registry
        )
        g_scraped.set(stocks_scraped)
        
        # Métrique : Actions matchées avec notre BDD
        g_matched = Gauge(
            'scraping_stocks_matched_count',
            'Number of stocks matched with our database by ISIN',
            registry=registry
        )
        g_matched.set(stocks_matched)
        
        # Métrique : Actions mises à jour
        g_updated = Gauge(
            'scraping_stocks_updated_count',
            'Number of stocks actually updated in database',
            registry=registry
        )
        g_updated.set(stocks_updated)
        
        # Métrique : Historiques créés
        g_hist_created = Gauge(
            'scraping_history_created_count',
            'Number of new StockPriceHistory records created',
            registry=registry
        )
        g_hist_created.set(history_created)
        
        # Métrique : Historiques mis à jour
        g_hist_updated = Gauge(
            'scraping_history_updated_count',
            'Number of StockPriceHistory records updated',
            registry=registry
        )
        g_hist_updated.set(history_updated)
        
        # Métrique : Taux de match
        g_match_rate = Gauge(
            'scraping_match_rate_percent',
            'Match rate percentage (matched/scraped)',
            registry=registry
        )
        g_match_rate.set(match_rate)
        
        # Métrique : Timestamp de dernière exécution
        g_timestamp = Gauge(
            'scraping_last_execution_timestamp',
            'Timestamp of last scraping execution',
            registry=registry
        )
        g_timestamp.set(time.time())
        
        # Métrique : Erreur si échec
        if not success and error_message:
            g_error = Gauge(
                'scraping_error',
                'Scraping error information',
                ['error_message'],
                registry=registry
            )
            g_error.labels(error_message=error_message[:100]).set(1)  # Limiter à 100 chars
        
        # Pousser les métriques vers le Pushgateway
        try:
            pushadd_to_gateway(
                self.pushgateway_url,
                job='scraping_intraday',
                registry=registry,
                grouping_key={'job_type': 'scraping'}
            )
            print(f"✅ Métriques scraping poussées (success={success}, duration={duration:.2f}s, scraped={stocks_scraped}, matched={stocks_matched}, updated={stocks_updated})")
        except Exception as e:
            print(f"❌ Erreur lors du push des métriques scraping: {e}")


# Instance globale
metrics_handler = MetricsHandler()


def track_job_execution(job_name):
    """
    Décorateur pour tracker automatiquement l'exécution d'un job
    
    Usage:
        @track_job_execution("export_transactions_PEA")
        def ma_fonction():
            # code du job
            return nombre_enregistrements  # optionnel
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            records = 0
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                # Si la fonction retourne un nombre, c'est le nombre d'enregistrements
                if isinstance(result, int):
                    records = result
                return result
            except Exception as e:
                error_message = str(e)
                raise
            finally:
                duration = time.time() - start_time
                metrics_handler.push_job_metrics(
                    job_name=job_name,
                    success=success,
                    duration=duration,
                    records=records,
                    error_message=error_message
                )
        
        return wrapper
    return decorator
