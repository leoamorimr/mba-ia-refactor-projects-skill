"""Notification side-effects extracted out of the HTTP layer. Previously
`criar_pedido`/`atualizar_status_pedido` in controllers.py printed
"ENVIANDO EMAIL/SMS/PUSH" directly in the route handler; this gives that
behavior one place to live (and to later swap for a real
email/SMS/push/queue integration) and replaces the `print()` calls with
structured logging.
"""
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def notify_order_created(self, pedido_id, usuario_id):
        logger.info("Enviando email: pedido %s criado para usuário %s", pedido_id, usuario_id)
        logger.info("Enviando SMS: seu pedido foi recebido!")
        logger.info("Enviando push: novo pedido recebido pelo sistema")

    def notify_order_approved(self, pedido_id):
        logger.info("Pedido %s aprovado. Preparar envio.", pedido_id)

    def notify_order_cancelled(self, pedido_id):
        logger.info("Pedido %s cancelado. Estoque devolvido.", pedido_id)
