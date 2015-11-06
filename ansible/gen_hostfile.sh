#
# Script to generate ansible host file from undercloud nova-list
#
#
. ~/stackrc
compute=()
controllers=()
ceph=()
while read line; do
 host=$(echo $line| awk '{print $4}')
 IP=$(echo $line | awk '{print $12}' | cut -d "=" -f2)
 if [[ ${host} =~ compute ]]; then
   compute+="$IP "
 fi
 if [[ ${host} =~ ceph ]] ; then
   ceph+="$IP "
 fi
 if [[ ${host} =~ control ]]; then
   controllers+="$IP "
 fi
done < <(nova list | grep over)
if [[ ${#compute} -gt 0 ]]; then
echo "[computes]"
for c in ${compute[@]}; do
  echo $c
done
fi
if [[ ${#controllers} -gt 0 ]]; then
echo ""
echo "[controllers]"
for ct in ${controllers[@]}; do
 echo $ct
done
fi
if [[ ${#ceph} -gt 0 ]]; then
echo ""
echo "[ceph]"
for ceph in ${ceph[@]}; do
 echo $ceph
done
fi
