'use client';

import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Stack from '@mui/material/Stack';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Stepper from '@mui/material/Stepper';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { APP_NAME, errorMessage, fieldErrors } from '@base/api/client';
import { isoDate } from '@base/lib/format';
import { useAuthStatusQuery, useOnboardingMutation } from '@base/store/api';
import { signedIn } from '@base/store/authSlice';
import { useAppDispatch, useAppSelector } from '@base/store/hooks';

interface AccountDraft {
  name: string;
  holder: string;
  opening_balance: string;
}

const STEPS = ['Konto anlegen', 'Haushalt', 'Bankkonten'];

export default function OnboardingPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const ready = useAppSelector((state) => state.auth.ready);

  const { data: status } = useAuthStatusQuery(undefined, { skip: !ready });
  const [onboard, { isLoading }] = useOnboardingMutation();

  const [step, setStep] = useState(0);
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [householdName, setHouseholdName] = useState('Unser Haushalt');
  const [horizon, setHorizon] = useState('24');
  const [savingsGoal, setSavingsGoal] = useState('');
  const [goalDate, setGoalDate] = useState('');

  const [accounts, setAccounts] = useState<AccountDraft[]>([
    { name: 'Gemeinsames Konto', holder: '', opening_balance: '0' },
  ]);

  useEffect(() => {
    if (status && !status.needs_onboarding) router.replace('/login');
  }, [router, status]);

  const updateAccount = (index: number, patch: Partial<AccountDraft>) =>
    setAccounts((current) =>
      current.map((account, position) => (position === index ? { ...account, ...patch } : account)),
    );

  const submit = async () => {
    setError('');
    setErrors({});
    try {
      const result = await onboard({
        name,
        email,
        password,
        household_name: householdName,
        prediction_horizon_months: Number(horizon) || 24,
        savings_goal: savingsGoal ? Number(savingsGoal) : null,
        savings_goal_date: goalDate || null,
        accounts: accounts.filter((account) => account.name.trim()),
      }).unwrap();
      dispatch(signedIn(result));
      router.replace('/dashboard');
    } catch (caught) {
      setError(errorMessage(caught));
      setErrors(fieldErrors(caught));
      const fields = Object.keys(fieldErrors(caught));
      if (fields.some((field) => ['name', 'email', 'password'].includes(field))) setStep(0);
    }
  };

  const canContinue = step === 0 ? name && email && password.length >= 8 : true;

  return (
    <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '100dvh', p: 2 }}>
      <Card sx={{ width: '100%', maxWidth: 560 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3}>
            <Stack spacing={0.5}>
              <Typography variant="h2">{APP_NAME} einrichten</Typography>
              <Typography variant="body2" color="text.secondary">
                Drei kurze Schritte, dann kann geplant werden.
              </Typography>
            </Stack>

            <Stepper activeStep={step} alternativeLabel>
              {STEPS.map((label) => (
                <Step key={label}><StepLabel>{label}</StepLabel></Step>
              ))}
            </Stepper>

            {error ? <Alert severity="error">{error}</Alert> : null}

            {step === 0 && (
              <Stack spacing={2}>
                <TextField
                  label="Dein Name" required autoFocus value={name}
                  error={Boolean(errors.name)} helperText={errors.name}
                  onChange={(event) => setName(event.target.value)}
                />
                <TextField
                  label="E-Mail" type="email" required autoComplete="email" value={email}
                  error={Boolean(errors.email)} helperText={errors.email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <TextField
                  label="Passwort" type="password" required autoComplete="new-password"
                  value={password}
                  error={Boolean(errors.password)}
                  helperText={errors.password || 'Mindestens 8 Zeichen'}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Stack>
            )}

            {step === 1 && (
              <Stack spacing={2}>
                <TextField
                  label="Name des Haushalts" value={householdName}
                  onChange={(event) => setHouseholdName(event.target.value)}
                />
                <TextField
                  label="Prognosehorizont" type="number" value={horizon}
                  slotProps={{
                    htmlInput: { min: 1, max: 600 },
                    input: { endAdornment: <InputAdornment position="end">Monate</InputAdornment> },
                  }}
                  helperText="Wie weit die Planung in die Zukunft rechnet."
                  onChange={(event) => setHorizon(event.target.value)}
                />
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                  <TextField
                    label="Sparziel" type="number" value={savingsGoal}
                    slotProps={{
                      input: { endAdornment: <InputAdornment position="end">€</InputAdornment> },
                    }}
                    onChange={(event) => setSavingsGoal(event.target.value)}
                  />
                  <TextField
                    label="bis" type="date" value={goalDate}
                    slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: isoDate(new Date()) } }}
                    onChange={(event) => setGoalDate(event.target.value)}
                  />
                </Stack>
              </Stack>
            )}

            {step === 2 && (
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">
                  Konten lassen sich später jederzeit ergänzen.
                </Typography>
                {accounts.map((account, index) => (
                  <Stack key={index} direction="row" spacing={1} alignItems="flex-start">
                    <TextField
                      label="Konto" value={account.name}
                      onChange={(event) => updateAccount(index, { name: event.target.value })}
                    />
                    <TextField
                      label="Inhaber" value={account.holder}
                      onChange={(event) => updateAccount(index, { holder: event.target.value })}
                    />
                    <TextField
                      label="Startsaldo" type="number" value={account.opening_balance}
                      sx={{ maxWidth: 150 }}
                      slotProps={{
                        input: { endAdornment: <InputAdornment position="end">€</InputAdornment> },
                      }}
                      onChange={(event) =>
                        updateAccount(index, { opening_balance: event.target.value })
                      }
                    />
                    <IconButton
                      onClick={() =>
                        setAccounts((current) => current.filter((_item, position) => position !== index))
                      }
                      disabled={accounts.length === 1}
                      sx={{ mt: 0.5 }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                ))}
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  sx={{ alignSelf: 'flex-start' }}
                  onClick={() =>
                    setAccounts((current) => [
                      ...current,
                      { name: '', holder: '', opening_balance: '0' },
                    ])
                  }
                >
                  Konto
                </Button>
              </Stack>
            )}

            <Stack direction="row" justifyContent="space-between">
              <Button
                color="inherit"
                disabled={step === 0}
                onClick={() => setStep((value) => value - 1)}
              >
                Zurück
              </Button>
              {step < STEPS.length - 1 ? (
                <Button
                  variant="contained"
                  disabled={!canContinue}
                  onClick={() => setStep((value) => value + 1)}
                >
                  Weiter
                </Button>
              ) : (
                <Button variant="contained" disabled={isLoading} onClick={submit}>
                  Loslegen
                </Button>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
