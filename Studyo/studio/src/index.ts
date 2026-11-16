import {getInputProps, registerRoot} from 'remotion';
import {RemotionRoot} from './Root';
import {kilavuzluKok} from './lib/yapim/KilavuzKok';

// Kılavuz kipi (yapım filmi, ./st yapim): yalnız girdi `yapim` verilince kök sarılır; girdisiz çizim eskisiyle aynı (kural 11).
const yapim = (() => {
  try {
    return Boolean((getInputProps() as {yapim?: unknown}).yapim);
  } catch {
    return false;
  }
})();
registerRoot(yapim ? kilavuzluKok(RemotionRoot) : RemotionRoot);
