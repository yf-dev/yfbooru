<?php
class EditUserSettingsJob extends AbstractJob
{
	protected $userRetriever;

	public function __construct()
	{
		$this->userRetriever = new UserRetriever($this);
	}

	public function execute()
	{
		$newSettings = $this->getArgument(JobArgs::ARG_NEW_SETTINGS);

		if (!is_array($newSettings))
			throw new SimpleException('Expected array');

		$user = $this->userRetriever->retrieve();
		foreach ($newSettings as $key => $value)
		{
			$user->getSettings()->set($key, $value);
		}

		if ($user->getAccessRank()->toInteger() == AccessRank::Anonymous)
			return $user;

		return UserModel::save($user);
	}

	public function getRequiredArguments()
	{
		return JobArgs::Conjunction(
			$this->userRetriever->getRequiredArguments(),
			JobArgs::ARG_NEW_SETTINGS);
	}

	public function getRequiredMainPrivilege()
	{
		return Privilege::EditUserSettings;
	}

	public function getRequiredSubPrivileges()
	{
		return Access::getIdentity($this->userRetriever->retrieve());
	}

	public function isAuthenticationRequired()
	{
		return false;
	}

	public function isConfirmedEmailRequired()
	{
		return false;
	}
}