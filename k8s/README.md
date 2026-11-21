# Despliegue en Kubernetes

| Manifiesto | Recursos | Función |
|---|---|---|
| `namespace.yaml` | Namespace `motopartes` | Agrupa los recursos del sistema |
| `configmap.yaml` | ConfigMap | URLs internas de los servicios y variables no sensibles |
| `secret.yaml` | 2 Secrets | JWT, contraseñas, cadenas de conexión y script de inicialización de MySQL |
| `mysql.yaml` | StatefulSet + Service headless + PVC 2Gi | Base de datos con almacenamiento persistente |
| `autenticacion.yaml` | Deployment + Service ClusterIP | Usuarios y Autenticación |
| `catalogo.yaml` | Deployment + Service ClusterIP + HPA | Catálogo (2 a 5 réplicas) |
| `inventario.yaml` | Deployment + Service ClusterIP + HPA | Inventario (2 a 5 réplicas, el de mayor carga) |
| `compras.yaml` | Deployment + Service ClusterIP | Compras y Proveedores |
| `reportes.yaml` | Deployment + Service ClusterIP | Reportes y Alertas |
| `gateway.yaml` | Deployment + Service **NodePort 30080** + HPA | API Gateway: único punto de entrada |
| `kustomization.yaml` | — | Permite aplicar todo con `kubectl apply -k k8s/` |

Decisiones:

- **Service Discovery:** cada Deployment tiene un Service con el mismo nombre; los servicios se llaman por DNS
  interno (`http://inventario:5000`). Las URLs están en el ConfigMap.
- **Redes:** solo el Gateway es `NodePort`; los demás son `ClusterIP` (no accesibles desde fuera del clúster).
- **Volúmenes:** MySQL usa un `PersistentVolumeClaim` (`volumeClaimTemplates`), los datos sobreviven a reinicios del pod.
- **Variables de entorno:** `envFrom` del ConfigMap + `secretKeyRef` para credenciales.
- **Salud:** `readinessProbe` y `livenessProbe` sobre `/health` (los servicios con BD verifican la conexión).
- **Escalado:** HPA por CPU (70 %) para Gateway, Catálogo e Inventario. Requiere `metrics-server`.
- **Actualizaciones:** `RollingUpdate` con `maxUnavailable: 0` para no cortar el servicio al desplegar.

## Pasos (minikube)

```bash
minikube start --cpus 4 --memory 6g
minikube addons enable metrics-server

# Construir las imágenes dentro del Docker de minikube (no hace falta subirlas a un registro)
eval $(minikube docker-env)
for s in gateway usuarios catalogo inventario compras reportes; do
  docker build -t motopartes/$s:1.0 ../servicios/$s
done

kubectl apply -k .
kubectl get pods -n motopartes -w
```

En Windows (PowerShell) el paso de `docker-env` es:

```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
foreach ($s in "gateway","usuarios","catalogo","inventario","compras","reportes") { docker build -t "motopartes/${s}:1.0" "..\servicios\$s" }
```

URL del Gateway: `http://$(minikube ip):30080` (con el driver Docker en Windows/Mac puede ser necesario
`minikube service gateway -n motopartes --url`).

## Comandos útiles para la demo

```bash
kubectl get all -n motopartes
kubectl get hpa -n motopartes
kubectl scale deployment inventario --replicas=3 -n motopartes
kubectl logs -n motopartes -l app=gateway --tail=20
kubectl delete pod -n motopartes -l app=reportes   # Kubernetes lo recrea solo
kubectl rollout restart deployment catalogo -n motopartes
```
