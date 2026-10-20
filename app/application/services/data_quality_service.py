"""Auditoría reproducible del escenario predictivo, sin alterar el modelo ML."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
from config import FEATURES_ACTUALES_PATH

class DataQualityService:
    def __init__(self, product_repository, features_path: Path = FEATURES_ACTUALES_PATH):
        self.products=product_repository
        self.features_path=Path(features_path)

    @staticmethod
    def _population_stability_index(reference, observed):
        """PSI descriptivo; no constituye medición formal de impacto del clasificador."""
        ref=np.asarray(reference,dtype=float)
        obs=np.asarray(observed,dtype=float)
        if len(ref)<10 or len(obs)<10:
            return None
        edges=np.unique(np.quantile(ref,np.linspace(0,1,11)))
        if len(edges)<3:
            return None
        edges[0]=-np.inf;edges[-1]=np.inf
        a=np.histogram(ref,bins=edges)[0]/len(ref)
        b=np.histogram(obs,bins=edges)[0]/len(obs)
        epsilon=1e-6
        a=np.maximum(a,epsilon);b=np.maximum(b,epsilon)
        return round(float(np.sum((b-a)*np.log(b/a))),4)

    def audit(self, inventory=None, today=None):
        inventory=self.products.get_prediction_inventory() if inventory is None else inventory
        today=today or date.today()
        base=pd.read_csv(self.features_path,usecols=['fecha','producto_id','stock_actual',
                                                        'stock_seguridad','punto_reorden','lead_time_dias'])
        base['producto_id']=base['producto_id'].astype(str).str.strip().str.upper()
        base=base.drop_duplicates('producto_id',keep='last')
        baseline={r['producto_id']:r for r in base.to_dict('records')}
        cut=pd.to_datetime(base['fecha'],errors='coerce').max()
        fecha=str(cut.date()) if pd.notna(cut) else None
        freshness=(today-cut.date()).days if pd.notna(cut) else None
        errors=[];missing=[];duplicate=[];ids=set();joined=[]
        for product in inventory:
            pid=str(product.get('producto_id') or '').strip().upper()
            if not pid or pid in ids:
                duplicate.append(pid or '(vacío)')
            ids.add(pid)
            if pid not in baseline:
                missing.append(pid)
            try:
                stock=float(product.get('stock_actual'))
                safety=float(product.get('stock_seguridad'))
                reorder=float(product.get('punto_reorden'))
                lead=float(product.get('lead_time_dias'))
                if not all(np.isfinite([stock,safety,reorder,lead])) or min(stock,safety,reorder)<0 or lead<1:
                    raise ValueError('Rango incorrecto')
            except (ValueError,TypeError):
                errors.append(pid);continue
            if pid in baseline:
                joined.append((float(baseline[pid]['stock_actual']),stock))
        psi=self._population_stability_index([a for a,b in joined],[b for a,b in joined]) if joined else None
        age_limit=7
        alerts=[]
        if not inventory: alerts.append('No se recibieron productos activos del inventario; revisar MySQL y permisos.')
        if inventory and not joined: alerts.append('Ningún producto operativo coincide con la referencia histórica.')
        if errors: alerts.append('Hay valores de stock o reposición inválidos.')
        if missing: alerts.append('Existen productos operativos sin historial de variables.')
        if duplicate: alerts.append('Existen identificadores duplicados o vacíos.')
        if freshness is None or freshness>age_limit: alerts.append('Las variables históricas no están actualizadas para uso operativo.')
        if psi is not None and psi>=0.25: alerts.append('Desplazamiento alto en la distribución del stock respecto a la referencia.')
        return {
            'estado':'REVISAR' if alerts else 'OK',
            'fecha_corte_variables':fecha,
            'dias_desde_corte':freshness,
            'umbral_frescura_dias':age_limit,
            'total_inventario':len(inventory),
            'total_referencia':len(baseline),
            'productos_sin_historial':len(missing),
            'ids_sin_historial':missing[:20],
            'ids_duplicados':duplicate[:20],
            'productos_con_campos_invalidos':len(errors),
            'ids_invalidos':errors[:20],
            'productos_comparables':len(joined),
            'psi_stock':psi,
            'interpretacion_psi':('Sin datos suficientes' if psi is None else
                                'Alto (>=0.25)' if psi>=0.25 else
                                'Moderado (>=0.10)' if psi>=0.10 else 'Bajo (<0.10)'),
            'observaciones':alerts,
            'aviso':'PSI y frescura son monitoreo de datos; no demuestran Recall en producción ni reemplazan validación con quiebres reales.',
        }
