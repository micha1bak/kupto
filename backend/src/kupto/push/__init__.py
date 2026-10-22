"""Infrastruktura Web Push: klucze VAPID, subskrypcje urządzeń i wysyłka powiadomień (#27).

API wysyłki: `kupto.push.notifier.Notifier` (w handlerach `kupto.deps.NotifierDep`), treść:
`kupto.push.notification.Notification` / `NotificationType`. Pakiet celowo niczego nie importuje,
żeby `python -m kupto.push.keys` działało bez ostrzeżeń.
"""
