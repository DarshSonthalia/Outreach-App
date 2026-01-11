from datetime import datetime

class WarmupService:

    @staticmethod
    def is_enabled(workspace):
        return workspace.warmup_enabled is True

    @staticmethod
    def current_day(domain):
        if not domain.created_at:
            return 1
        return (datetime.utcnow() - domain.created_at).days + 1

    @staticmethod
    def daily_limit(workspace, domain):
        if not WarmupService.is_enabled(workspace):
            return None
        if domain.warmup_completed:
            return None

        limits = {
            1: 5,
            2: 8,
            3: 12,
            4: 18,
            5: 25,
            6: 35,
            7: 50
        }

        return limits.get(WarmupService.current_day(domain))

    @staticmethod
    def complete(domain):
        domain.warmup_completed = True
