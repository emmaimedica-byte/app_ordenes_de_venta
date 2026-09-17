from datetime import datetime

from app.models.orden import EstadoOrden, OrdenVenta


class DashboardService:

    def calcular_metricas(
        self,
        ordenes: list[OrdenVenta],
    ) -> dict:

        total_ordenes = len(ordenes)

        completadas = len([
            orden
            for orden in ordenes
            if orden.estado == EstadoOrden.ADMINISTRACION_COMPLETADO
        ])

        activas = total_ordenes - completadas

        alertas = len([
            orden
            for orden in ordenes
            if (
                orden.estado != EstadoOrden.ADMINISTRACION_COMPLETADO
                and (
                    datetime.now() - orden.actualizado_en
                ).total_seconds() > 86400
            )
        ])

        return {
            "total_ordenes": total_ordenes,
            "completadas": completadas,
            "activas": activas,
            "alertas": alertas,
        }


    def calcular_distribucion_por_etapa(
        self,
        ordenes: list[OrdenVenta],
    ) -> dict:

        distribucion = {}

        for estado in EstadoOrden:
            distribucion[estado.value] = len([
                orden
                for orden in ordenes
                if orden.estado == estado
            ])

        return distribucion